# Missing Tests Report

Updated on March 18, 2026.

Audit basis:
- Full suite run: `530 passed, 1 skipped, 0 failed`
- Coverage source: fresh run via `coverage run --source=app -m pytest -q`
- Coverage snapshot: `96%` (`8805` statements, `356` missing)
- This file tracks only still-open test gaps.

## 1) Removed as Covered

Newly closed from the previous backlog:

- `app/database.py` -> `100%`
- `app/signature_requests/services/signer_actions.py` -> `93%` (from 70%)
- `app/dashboard/services/dashboard_quick_actions_builder.py` -> `100%`
- `app/dashboard/services/_quick_actions_helpers.py` -> `100%`
- `app/vat_reports/api/routes_client_summary.py` -> `96%`
- `app/annual_reports/services/tax_engine.py` -> `100%`
- `app/search/services/document_search_service.py` -> `100%`
- `app/clients/api/clients_excel.py` -> `98%`
- `app/annual_reports/repositories/report_lifecycle_repository.py` -> `100%`
- `app/annual_reports/services/status_service.py` -> `100%`
- `app/clients/services/client_lookup.py` -> `100%`
- `app/vat_reports/api/routes_status.py` -> `100%`
- `app/vat_reports/services/intake.py` -> `98%`
- `app/binders/services/binder_list_service.py` -> `93%`

## 2) Current Critical Gaps (<85% coverage)

- `app/health/services/health_service.py` (`82%`, missing lines: `15-16`)
  - Add negative-path health check tests.
- `app/core/env_validator.py` (`84%`, missing lines: `34-35, 54-56`)
  - Add stderr formatting assertions for missing+empty vars together.

## 3) Current High-Priority Gaps (85-90% coverage)

- `app/vat_reports/services/data_entry_invoices.py` (`85%`, missing: `55, 74, 76, 78-81, 108`)
- `app/authority_contact/api/authority_contact.py` (`85%`, missing: `85-92`)
- `app/charge/api/charge.py` (`86%`, missing: `133-135, 145-152, 162-164`)
- `app/annual_reports/api/annual_report_status.py` (`86%`, missing: `69-72`)
- `app/charge/services/billing_service.py` (`86%`, missing: `45, 106, 135, 141, 161-171`)
- `app/dashboard/services/dashboard_extended_service.py` (`87%`, missing: `98-105`)
- `app/core/background_jobs.py` (`87%`, missing: `32-34, 50-51`)
- `app/utils/excel.py` (`88%`, missing: `42-43, 79-80, 130`)
- `app/annual_reports/services/financial_tax_service.py` (`88%`, missing: `71-77`)
- `app/binders/services/binder_intake_service.py` (`88%`, missing: `45-51`)
- `app/main.py` (`88%`, missing: `27, 32, 57-59`)
- `app/correspondence/services/correspondence_service.py` (`88%`, missing: `72-74, 81, 90`)
- `app/annual_reports/services/advances_summary_service.py` (`88%`, missing: `20, 41, 45`)
- `app/tax_deadline/services/tax_deadline_service.py` (`89%`, missing: `56, 59, 89, 110, 119, 131, 174-178`)
- `app/annual_reports/services/create_service.py` (`89%`, missing: `41, 49, 60, 70`)
- `app/users/services/user_management_service.py` (`89%`, missing: `34, 75, 79-80, 86, 90, 106, 126`)
- `app/annual_reports/repositories/schedule_repository.py` (`89%`, missing: `16, 65-73`)
- `app/reminders/api/routes_create.py` (`89%`, missing: `41, 55, 69`)
- `app/vat_reports/repositories/vat_invoice_repository.py` (`89%`, missing: `132-146, 151, 162`)
- `app/vat_reports/services/data_entry_common.py` (`89%`, missing: `24, 113-116`)
- `app/search/services/search_service.py` (`89%`, missing: `80-88, 120, 122, 124`)
- `app/config.py` (`89%`, missing: `9-10, 15, 25, 50`)
- `app/reminders/services/status_changes.py` (`89%`, missing: `12, 33`)
- `app/vat_reports/services/data_entry_invoice_delete.py` (`89%`, missing: `27, 33`)
- `app/clients/repositories/client_repository.py` (`90%`, missing: `73, 76-77, 94-95, 118, 144`)
- `app/permanent_documents/services/permanent_document_service.py` (`90%`, missing: `59, 62, 71-72, 89-90, 97, 136`)
- `app/reminders/services/factory.py` (`90%`, missing: `30, 32, 65, 100, 102`)
- `app/infrastructure/notifications.py` (`90%`, missing: `114-116, 182-185`)
- `app/clients/services/client_excel_service.py` (`90%`, missing: `69-70, 98, 108-109, 123-124`)

## 4) Next Target

1. Close `<85%` files first (`health_service`, `env_validator`).
2. Then reduce the broad `85-90%` group, starting with API boundary handlers and service orchestrators.
3. Coverage goal after this pass: raise total from `96%` toward `>=97%`.
