# Missing Tests Report

Updated on March 18, 2026.

Audit basis:
- Test status used for this audit (no rerun): `490 passed, 1 skipped, 0 failed`
- Coverage source: existing `.coverage` artifact in repo
- Coverage snapshot from artifact: `94%` (`8805` statements, `511` missing)
- This file tracks only still-open test gaps.

## 1) Removed as Covered

The following previously listed gaps are now covered and removed from the backlog:

- `app/annual_reports/services/annual_report_pdf_service.py` -> `98%`
- `app/tax_deadline/services/deadline_generator.py` -> `100%`
- `app/charge/services/bulk_billing_service.py` -> `100%`
- `app/permanent_documents/services/permanent_document_action_service.py` -> `100%`
- `app/advance_payments/services/advance_payment_generator.py` -> `100%`
- `app/core/background_jobs.py` -> `87%`
- `app/infrastructure/notifications.py` -> `90%`
- `app/clients/services/client_service.py` -> `96%`
- `app/annual_reports/repositories/income_repository.py` -> `100%`
- `app/annual_reports/repositories/expense_repository.py` -> `100%`
- `app/annual_reports/api/routes_export.py` -> `100%`
- `app/annual_reports/api/annual_report_create_read.py` -> `100%`
- `app/annual_reports/api/annual_report_kanban.py` -> `100%`
- `app/reminders/api/routes_mark_sent.py` -> `100%`
- `app/tax_deadline/api/deadline_generate.py` -> `100%`
- `app/tax_deadline/repositories/tax_deadline_repository.py` -> `93%`
- `app/utils/excel.py` -> `88%`
- `app/reports/api/reports.py` -> `96%`
- `app/permanent_documents/api/permanent_document_actions.py` -> `100%`
- `app/binders/api/binders_list_get.py` -> `100%`
- `app/binders/api/binders_history.py` -> `100%`
- `app/reminders/services/factory.py` -> `90%`

## 2) Still-Open Critical Gaps (<75% coverage)

- `app/database.py` (`62%`, missing lines: `8, 26-30`)
  - Add tests for engine/session setup and metadata create path.
- `app/signature_requests/services/signer_actions.py` (`70%`, missing lines: `79-100`)
  - Add tests for `_auto_advance_annual_report()` negative/no-op branches.
- `app/dashboard/services/dashboard_quick_actions_builder.py` (`72%`, missing lines: `42-49`)
  - Add tests for low-signal branches where no actions should be returned.
- `app/vat_reports/api/routes_client_summary.py` (`74%`, missing lines: `48-54`)
  - Add API tests for export error handling and response mapping.
- `app/dashboard/services/_quick_actions_helpers.py` (`74%`, missing lines: `43-44, 70-75, 78, 103-113, 124-137`)
  - Add focused tests for uncovered helper branches in VAT/annual actions.

## 3) Still-Open High-Priority Gaps (75-84% coverage)

- `app/annual_reports/services/tax_engine.py` (`76%`, missing lines: `107-112, 120-125`)
  - Add edge-case bracket/credit calculations.
- `app/infrastructure/storage.py` (`76%`, missing lines: `109-110, 135-142, 146-147, 160-166, 183-198`)
  - Add S3 error/edge-path tests and provider selection fallback.
- `app/search/services/document_search_service.py` (`79%`, missing lines: `22-25`)
  - Add empty-query/filter branch tests.
- `app/clients/api/clients_excel.py` (`79%`, missing lines: `27-28, 46-47, 72, 79-80, 87, 93-94`)
  - Add template/export/import failure branch tests.
- `app/notification/services/notification_service.py` (`81%`, missing lines: `78, 130-131, 137-152, 172-173, 178-179`)
  - Add send/skip/error branch tests for notification fan-out.
- `app/annual_reports/repositories/report_lifecycle_repository.py` (`81%`, missing lines: `38-44`)
  - Add lifecycle query edge branches.
- `app/annual_reports/services/financial_crud_service.py` (`81%`, missing lines: `42-45, 48, 54, 72, 90-93, 96, 102`)
  - Add update/delete validation and not-found branches.
- `app/annual_reports/services/schedule_service.py` (`81%`, missing lines: `20, 29-31, 41, 47`)
  - Add parsing/invalid schedule branches.
- `app/reminders/api/routes_create.py` (`81%`, missing lines: `22, 41, 55, 69-78`)
  - Add validation and role/error mapping tests.
- `app/binders/services/binder_list_service.py` (`82%`, missing lines: `72, 99, 104-108, 114, 117, 120, 134`)
  - Add filter-combination and edge pagination tests.
- `app/annual_reports/services/status_service.py` (`82%`, missing lines: `40, 57-59, 62-67, 83, 130, 134, 138`)
  - Add disallowed transition and side-effect branches.
- `app/clients/services/client_lookup.py` (`82%`, missing lines: `19, 21, 27`)
  - Add not-found and exact-match branch tests.
- `app/vat_reports/api/routes_status.py` (`82%`, missing lines: `51-57`)
  - Add endpoint failure mapping tests.
- `app/vat_reports/services/intake.py` (`84%`, missing lines: `19-27, 64, 116`)
  - Add intake validation and exceptional flow tests.

## 4) Next Target

1. Cover all `<75%` files first (`database`, `signer_actions`, dashboard quick actions, VAT client summary API).
2. Then close the `75-84%` list above.
3. Coverage goal after this pass: move total from `94%` toward `>=95%`.
