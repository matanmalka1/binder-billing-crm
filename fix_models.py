#!/usr/bin/env python3
"""
fix_models.py
-------------
Run from project root (backend/):
    python3 fix_models.py

Fixes:
  1. permanent_documents — document_type / status: String → pg_enum
  2. annual_reports      — partial unique index for soft-delete on (client_id, tax_year)
  3. all models          — remove unused Enum from sqlalchemy imports

Intentionally skipped (in use):
  - ReportStage                  → annual_reports/services/query_service.py
  - UrgencyLevel                 → tax_deadline/services/tax_deadline_service.py
  - supporting_document relation → schema populates supporting_document_filename from it
"""

import re

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def patch(path: str, old: str, new: str, label: str = "") -> bool:
    with open(path) as f:
        content = f.read()
    if old not in content:
        print(f"⚠️   {path} — '{label or old[:40]}' not found, skipping")
        return False
    with open(path, "w") as f:
        f.write(content.replace(old, new, 1))
    print(f"✅  {path}" + (f" — {label}" if label else ""))
    return True


# ══════════════════════════════════════════════════════════════════════════════
# 1. permanent_documents — String → pg_enum
# ══════════════════════════════════════════════════════════════════════════════
PD = "app/permanent_documents/models/permanent_document.py"

# Add pg_enum import
patch(PD,
    "from app.database import Base",
    "from app.utils.enum_utils import pg_enum\nfrom app.database import Base",
    "add pg_enum import")

# document_type: String → pg_enum(DocumentType)
patch(PD,
    "    document_type = Column(String, nullable=False)",
    "    document_type = Column(pg_enum(DocumentType), nullable=False)",
    "document_type String → pg_enum")

# status: String → pg_enum(DocumentStatus)
patch(PD,
    '    status = Column(String, default=DocumentStatus.PENDING, nullable=False, server_default="pending")',
    "    status = Column(pg_enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)",
    "status String → pg_enum")


# ══════════════════════════════════════════════════════════════════════════════
# 2. annual_reports — replace hard unique index with partial (soft-delete aware)
# ══════════════════════════════════════════════════════════════════════════════
AR = "app/annual_reports/models/annual_report_model.py"

patch(AR,
    '        Index("idx_annual_report_client_year", "client_id", "tax_year", unique=True),',
    '''\
        # Partial unique index: allows re-creating a report for the same year
        # after soft-delete (deleted_at IS NOT NULL means the slot is free again).
        Index(
            "idx_annual_report_client_year",
            "client_id",
            "tax_year",
            unique=True,
            postgresql_where=Column("deleted_at").is_(None),
        ),''',
    "hard unique → partial unique (soft-delete aware)")



# ══════════════════════════════════════════════════════════════════════════════
# 4. Remove unused `Enum` from sqlalchemy imports
# ══════════════════════════════════════════════════════════════════════════════

def remove_enum_from_import(path: str) -> None:
    with open(path) as f:
        content = f.read()

    # Only act if Enum( is not used directly (pg_enum wraps it internally)
    if re.search(r'\bEnum\(', content):
        print(f"–   {path} — Enum( still in use, skipping import cleanup")
        return

    original = content

    # Pattern: "Enum, " or ", Enum" or ", Enum," in SA import block
    content = re.sub(r',\s*Enum\b', '', content)   # trailing: ", Enum"
    content = re.sub(r'\bEnum\s*,\s*', '', content) # leading:  "Enum, "

    if content != original:
        with open(path, "w") as f:
            f.write(content)
        print(f"✅  {path} — remove unused Enum from SA import")
    else:
        print(f"–   {path} — Enum not found in imports, skipping")


for p in [
    "app/signature_requests/models/signature_request.py",
    "app/vat_reports/models/vat_work_item.py",
    "app/vat_reports/models/vat_invoice.py",
    "app/annual_reports/models/annual_report_model.py",
    "app/annual_reports/models/annual_report_status_history.py",
    "app/annual_reports/models/annual_report_income_line.py",
    "app/annual_reports/models/annual_report_expense_line.py",
    "app/annual_reports/models/annual_report_annex_data.py",
    "app/annual_reports/models/annual_report_schedule_entry.py",
    "app/authority_contact/models/authority_contact.py",
    "app/clients/models/client_tax_profile.py",
    "app/clients/models/client.py",
    "app/correspondence/models/correspondence.py",
    "app/notification/models/notification.py",
    "app/reminders/models/reminder.py",
    "app/tax_deadline/models/tax_deadline.py",
    "app/users/models/user_audit_log.py",
    "app/users/models/user.py",
]:
    remove_enum_from_import(p)


# ══════════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════════
print("""
── Next steps ────────────────────────────────────────────────────────────────
  1. Run migrations for permanent_documents enum change:
       APP_ENV=development alembic revision --autogenerate -m "fix: permanent_documents enums and annual_report partial index"
       APP_ENV=development alembic upgrade head

  2. Commit:
       git add -A
       git commit -m "fix: permanent_documents use pg_enum, annual_report partial unique index, clean unused Enum imports"
       git push origin main

  3. On Render: Deploy latest commit
     (alembic upgrade head runs automatically via Start Command)
""")