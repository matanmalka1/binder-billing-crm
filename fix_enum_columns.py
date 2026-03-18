#!/usr/bin/env python3
"""
fix_enum_columns.py
-------------------
Run from the project root (backend/):
    python3 fix_enum_columns.py

What it does:
  1. Creates app/utils/enum_utils.py with the pg_enum helper.
  2. In every model file that uses Column(Enum(...)):
       - Replaces  Column(Enum(XYZ))                  →  Column(pg_enum(XYZ))
       - Replaces  Column(Enum(XYZ, create_type=False))→  Column(pg_enum(XYZ, create_type=False))
       - Adds      from app.utils.enum_utils import pg_enum
       - Removes   Enum  from the sqlalchemy import if it's no longer used
"""

import re
import os

# ---------------------------------------------------------------------------
# 1. Create the helper module
# ---------------------------------------------------------------------------
ENUM_UTILS_PATH = "app/utils/enum_utils.py"
ENUM_UTILS_CONTENT = '''\
from sqlalchemy import Enum as SAEnum


def pg_enum(enum_class, **kwargs):
    """
    Drop-in replacement for Column(Enum(MyEnum)) that forces SQLAlchemy
    to use the Python enum\'s .value (e.g. "pending_signature") instead of
    its .name (e.g. "PENDING_SIGNATURE") when communicating with PostgreSQL.

    Background
    ----------
    SQLAlchemy\'s native PostgreSQL enum uses member *names* by default.
    When your Python enum uses lowercase values that differ from the uppercase
    names, every INSERT/SELECT sends the wrong string and PostgreSQL raises:
        invalid input value for enum ...: "PENDING_SIGNATURE"

    The fix is values_callable, which tells SQLAlchemy which strings to use
    as the enum labels — we always want the .value.

    Usage
    -----
    # Before
    status = Column(Enum(SignatureRequestStatus), nullable=False)

    # After
    from app.utils.enum_utils import pg_enum
    status = Column(pg_enum(SignatureRequestStatus), nullable=False)
    """
    return SAEnum(
        enum_class,
        values_callable=lambda x: [e.value for e in x],
        **kwargs,
    )
'''

os.makedirs(os.path.dirname(ENUM_UTILS_PATH), exist_ok=True)
with open(ENUM_UTILS_PATH, "w") as f:
    f.write(ENUM_UTILS_CONTENT)
print(f"✅  Created {ENUM_UTILS_PATH}")

# ---------------------------------------------------------------------------
# 2. Target files (from grep output)
# ---------------------------------------------------------------------------
TARGET_FILES = [
    "app/clients/models/client_tax_profile.py",
    "app/clients/models/client.py",
    "app/vat_reports/models/vat_work_item.py",
    "app/vat_reports/models/vat_invoice.py",
    "app/authority_contact/models/authority_contact.py",
    "app/charge/models/charge.py",
    "app/signature_requests/models/signature_request.py",
    "app/notification/models/notification.py",
    "app/tax_deadline/models/tax_deadline.py",
    "app/users/models/user.py",
    "app/users/models/user_audit_log.py",
    "app/binders/models/binder.py",
    "app/annual_reports/models/annual_report_annex_data.py",
    "app/annual_reports/models/annual_report_income_line.py",
    "app/annual_reports/models/annual_report_status_history.py",
    "app/annual_reports/models/annual_report_model.py",
    "app/annual_reports/models/annual_report_schedule_entry.py",
    "app/annual_reports/models/annual_report_expense_line.py",
    "app/reminders/models/reminder.py",
    "app/correspondence/models/correspondence.py",
]

PG_ENUM_IMPORT = "from app.utils.enum_utils import pg_enum\n"

# Regex: Column(Enum(  ...anything except nested parens...  ))
# Handles:  Enum(XYZ)  and  Enum(XYZ, create_type=False)
ENUM_PATTERN = re.compile(r'Enum\(([^()]+)\)')


def patch_file(path: str):
    if not os.path.exists(path):
        print(f"⚠️   {path} not found — skipping")
        return

    with open(path) as f:
        original = f.read()

    # Skip if there's nothing to replace
    if not ENUM_PATTERN.search(original):
        print(f"–   {path} — nothing to replace")
        return

    # Replace Enum(...)  →  pg_enum(...)
    patched = ENUM_PATTERN.sub(lambda m: f"pg_enum({m.group(1)})", original)

    # Add pg_enum import if not already present
    if PG_ENUM_IMPORT.strip() not in patched:
        # Insert after the last SQLAlchemy import line for tidiness,
        # or before the first non-blank, non-comment line if no SA import found.
        lines = patched.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("from sqlalchemy") or line.startswith("import sqlalchemy"):
                insert_at = i + 1  # after last SA import
        lines.insert(insert_at, PG_ENUM_IMPORT)
        patched = "".join(lines)

    # Clean up: if 'Enum' is no longer used directly, remove it from SA imports.
    # Pattern: "from sqlalchemy import ..., Enum, ..." or "from sqlalchemy import Enum"
    def remove_enum_from_sa_import(text):
        def replacer(m):
            imports = [s.strip() for s in m.group(1).split(",")]
            imports = [s for s in imports if s != "Enum"]
            if not imports:
                return ""          # entire import line removed
            return f"from sqlalchemy import {', '.join(imports)}"
        return re.sub(
            r'from sqlalchemy import ([^\n]+)',
            replacer,
            text,
        )

    # Only clean if Enum is truly gone as a standalone reference
    if "Enum(" not in patched and re.search(r'\bEnum\b', patched):
        # Enum is still referenced (e.g. PyEnum alias) — don't touch imports
        pass
    elif "Enum(" not in patched:
        patched = remove_enum_from_sa_import(patched)
        # Remove any blank lines left by empty imports
        patched = re.sub(r'\n{3,}', '\n\n', patched)

    if patched == original:
        print(f"–   {path} — already up to date")
        return

    with open(path, "w") as f:
        f.write(patched)
    print(f"✅  {path}")


# ---------------------------------------------------------------------------
# 3. Run
# ---------------------------------------------------------------------------
print("\n── Patching model files ──────────────────────────────────────────────")
for fp in TARGET_FILES:
    patch_file(fp)

# ---------------------------------------------------------------------------
# 4. Verify: make sure no Column(Enum( remains
# ---------------------------------------------------------------------------
print("\n── Verification ──────────────────────────────────────────────────────")
remaining = []
for fp in TARGET_FILES:
    if not os.path.exists(fp):
        continue
    with open(fp) as f:
        content = f.read()
    # pg_enum is fine; raw Enum( inside Column is the problem
    hits = re.findall(r'Column\(Enum\(', content)
    if hits:
        remaining.append((fp, len(hits)))

if remaining:
    print("❌  These files still have Column(Enum(:")
    for fp, n in remaining:
        print(f"    {fp}  ({n} occurrence{'s' if n>1 else ''})")
else:
    print("✅  All Column(Enum(...)) replaced with Column(pg_enum(...))")

print("\n── Next steps ────────────────────────────────────────────────────────")
print("  git add -A")
print('  git commit -m "fix: use pg_enum values_callable so SQLAlchemy sends lowercase enum values to PostgreSQL"')
print("  git push origin main")
print("  → Deploy on Render (no DB migration needed — schema is already correct)")
