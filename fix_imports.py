import re, os

files = [
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

IMPORT_LINE = "from app.utils.enum_utils import pg_enum\n"

for path in files:
    with open(path) as f:
        content = f.read()

    # Remove the misplaced import wherever it is (inside or outside SA block)
    content = content.replace(IMPORT_LINE, "")

    # Find the closing ) of the sqlalchemy import block, insert after it
    # Pattern: find "from sqlalchemy import (\n....\n)\n"
    match = re.search(r'(from sqlalchemy import \([^)]+\)\n)', content)
    if match:
        end = match.end()
        content = content[:end] + IMPORT_LINE + content[end:]
        print(f"✅  {path}")
    else:
        # Fallback: insert after last "from sqlalchemy" line
        lines = content.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("from sqlalchemy"):
                insert_at = i + 1
        lines.insert(insert_at, IMPORT_LINE)
        content = "".join(lines)
        print(f"✅  {path} (fallback)")

    with open(path, "w") as f:
        f.write(content)

print("\nDone. Verify:")
print('  head -35 app/signature_requests/models/signature_request.py')
