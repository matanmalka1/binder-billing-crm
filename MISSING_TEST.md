# Missing Tests Report

Updated on March 18, 2026.

Audit basis:
- Full suite run: `567 passed, 1 skipped, 0 failed`
- Coverage source: `./.venv/bin/coverage run --source=app -m pytest -q`
- Coverage snapshot: `97%` (`8805` statements, `244` missing)
- This file tracks only still-open test gaps.

## 1) Removed as Covered

Closed from the previous backlog:

- `app/health/services/health_service.py` -> `100%`
- `app/core/env_validator.py` -> `100%`
- `app/vat_reports/services/data_entry_invoices.py` -> `98%`
- `app/authority_contact/api/authority_contact.py` -> `100%`
- `app/charge/api/charge.py` -> `95%`
- `app/annual_reports/api/annual_report_status.py` -> `97%`
- `app/charge/services/billing_service.py` -> `100%`
- `app/dashboard/services/dashboard_extended_service.py` -> `98%`
- `app/core/background_jobs.py` -> `95%`
- `app/utils/excel.py` -> `100%`
- `app/annual_reports/services/financial_tax_service.py` -> `98%`
- `app/annual_reports/services/advances_summary_service.py` -> `96%`
- `app/tax_deadline/services/tax_deadline_service.py` -> `96%`
- `app/annual_reports/services/create_service.py` -> `97%`
- `app/users/services/user_management_service.py` -> `97%`
- `app/reminders/api/routes_create.py` -> `100%`
- `app/vat_reports/services/data_entry_common.py` -> `100%`
- `app/vat_reports/services/data_entry_invoice_delete.py` -> `95%`
- `app/search/services/search_service.py` -> `100%`
- `app/clients/repositories/client_repository.py` -> `100%`
- `app/permanent_documents/services/permanent_document_service.py` -> `94%`
- `app/infrastructure/notifications.py` -> `96%`
- `app/clients/services/client_excel_service.py` -> `97%`

## 2) Current Critical Gaps (<85% coverage)

No files currently below `85%`.

## 3) Current High-Priority Gaps (85-90% coverage)

- `app/binders/services/binder_intake_service.py` (`88%`, missing: `45-51`)
- `app/main.py` (`88%`, missing: `27, 32, 57-59`)
- `app/correspondence/services/correspondence_service.py` (`88%`, missing: `72-74, 81, 90`)
- `app/annual_reports/repositories/schedule_repository.py` (`89%`, missing: `16, 65-73`)
- `app/vat_reports/repositories/vat_invoice_repository.py` (`89%`, missing: `132-146, 151, 162`)
- `app/config.py` (`89%`, missing: `9-10, 15, 25, 50`)
- `app/reminders/services/status_changes.py` (`89%`, missing: `12, 33`)
- `app/reminders/services/factory.py` (`90%`, missing: `30, 32, 65, 100, 102`)

## 4) Next Target

1. Close router bootstrap/config gaps first: `main.py`, `config.py`.
2. Then service/repository branches: `correspondence_service`, `schedule_repository`, `vat_invoice_repository`.
3. Finish with reminder factory/status transitions and binder intake validation branches.
