# VAT Reports Module

> Last audited: 2026-03-22

Manages VAT work-item lifecycle per business and period: intake, data entry, review, filing, audit trail, and business-level summary/export.

## Scope

- Create one VAT work item per `business_id + period`
- Track lifecycle states until filed (immutable after filing)
- Add/update/delete invoices and recalculate VAT totals
- Advisor filing flow with optional override + mandatory justification
- Query work items, invoices, and audit trail
- Business summary and yearly export (Excel/PDF)

## API Base Path

Router is mounted under `/api/v1/vat` (via `app/router_registry.py` + `app/vat_reports/api/routers.py`).

## Access Control

- Most VAT endpoints require `ADVISOR` or `SECRETARY`
- Advisor-only endpoints:
  - `POST /api/v1/vat/work-items/{item_id}/send-back`
  - `POST /api/v1/vat/work-items/{item_id}/file`
  - `DELETE /api/v1/vat/work-items/{item_id}/invoices/{invoice_id}`

## Data Model

### `VatWorkItem`

Core fields:
- `id`
- `business_id` (FK, required)
- `created_by` (FK, required)
- `assigned_to` (FK, optional)
- `period` (`YYYY-MM`, required)
- `period_type` (`VatType` snapshot: monthly / bimonthly)
- `status` (`pending_materials`, `material_received`, `data_entry_in_progress`, `ready_for_review`, `filed`)
- `pending_materials_note` (optional)
- `total_output_vat`, `total_input_vat`, `net_vat`
- `total_output_net`, `total_input_net` (VAT form net snapshots)
- `final_vat_amount` (set when filed)
- `is_overridden`, `override_justification`
- `submission_method` (`online`, `manual`, `representative`)
- `submission_reference` (optional)
- `is_amendment`, `amends_item_id`
- `filed_at`, `filed_by`
- `created_at`, `updated_at`
- soft-delete fields: `deleted_at`, `deleted_by`

Constraint:
- unique per (`business_id`, `period`)

### `VatInvoice`

Core fields:
- `id`, `work_item_id`, `created_by`
- `invoice_type` (`income` / `expense`)
- `document_type` (`tax_invoice`, `transaction_invoice`, `receipt`, `consolidated`, `self_invoice`, `credit_note`)
- `invoice_number`, `invoice_date` (`date`)
- `counterparty_name`, `counterparty_id` (optional)
- `net_amount`, `vat_amount`
- `expense_category` (required for expense invoices)
- `rate_type` (`standard`, `exempt`, `zero_rate`)
- `deduction_rate` (derived from expense category)
- `is_exceptional` (derived: net amount > 25,000)
- `created_at`

Constraint:
- unique per (`work_item_id`, `invoice_type`, `invoice_number`)

### `VatAuditLog`

- `id`, `work_item_id`, `performed_by`, `performed_at`
- `action`
- `old_value`, `new_value`, `note`
- `invoice_id` (optional FK; set null on invoice deletion)

## Endpoints

### Intake

- `POST /api/v1/vat/work-items`
  - body: `business_id`, `period`, `assigned_to?`, `mark_pending?`, `pending_materials_note?`
- `POST /api/v1/vat/work-items/{item_id}/materials-complete`
  - transition: `pending_materials -> material_received`

### Data Entry

- `POST /api/v1/vat/work-items/{item_id}/invoices`
  - body includes: `invoice_type`, `net_amount`, `vat_amount`, optional identity/document fields
- `GET /api/v1/vat/work-items/{item_id}/invoices`
  - query: `invoice_type?`
- `PATCH /api/v1/vat/work-items/{item_id}/invoices/{invoice_id}`
  - partial invoice updates
- `DELETE /api/v1/vat/work-items/{item_id}/invoices/{invoice_id}` (advisor only)

### Status + Filing

- `POST /api/v1/vat/work-items/{item_id}/ready-for-review`
  - transition: `data_entry_in_progress -> ready_for_review`
- `POST /api/v1/vat/work-items/{item_id}/send-back` (advisor only)
  - body: `correction_note`
  - transition: `ready_for_review -> data_entry_in_progress`
- `POST /api/v1/vat/work-items/{item_id}/file` (advisor only)
  - body: `submission_method`, `override_amount?`, `override_justification?`, `submission_reference?`, `is_amendment?`, `amends_item_id?`

### Queries

- `GET /api/v1/vat/work-items/{item_id}`
- `GET /api/v1/vat/businesses/{business_id}/work-items`
- `GET /api/v1/vat/work-items`
  - query: `status?`, `page` (default `1`), `page_size` (default `20`, max `200`), `period?`, `business_name?`
- `GET /api/v1/vat/work-items/{item_id}/audit`
- `GET /api/v1/vat/businesses/{business_id}/summary`
- `GET /api/v1/vat/businesses/{business_id}/export`
  - query: `format=excel|pdf`, `year` (`2000-2100`)

## Business Rules

- `period` must match `YYYY-MM`
- duplicate work item for the same (`business_id`, `period`) is rejected
- if `mark_pending=true`, `pending_materials_note` is required
- VAT-exempt businesses cannot open VAT work items
- bi-monthly businesses cannot open even-month periods
- first invoice on `material_received` auto-transitions to `data_entry_in_progress`
- invoices can be added only in `material_received`, `data_entry_in_progress`, or `ready_for_review`
- work item is immutable after `filed`
- `expense` invoice requires `expense_category`
- `tax_invoice` expense requires `counterparty_id`
- `net_amount` must be `> 0`; `vat_amount` must be `>= 0`
- filing requires current status `ready_for_review`
- override filing amount requires `override_justification`
- invoice changes recalculate totals and append audit records

## Notes From Audit

- API and model are business-scoped (`business_id`), not client-scoped
- filing field is `submission_method` (not `filing_method`)
- query endpoints expose deadline enrichment fields on work-item responses: `submission_deadline`, `days_until_deadline`, `is_overdue`

## References

- Models: `app/vat_reports/models/`
- Schemas: `app/vat_reports/schemas/`
- Routes: `app/vat_reports/api/`
- Services: `app/vat_reports/services/`
- Repositories: `app/vat_reports/repositories/`

Domain errors use stable codes such as:
- `VAT.NOT_FOUND`
- `VAT.CONFLICT`
- `VAT.INVALID_TRANSITION`
- `VAT.INVALID_STATUS`
- `VAT.PENDING_NOTE_REQUIRED`
- `VAT.JUSTIFICATION_REQUIRED`
- `VAT.EXPENSE_CATEGORY_REQUIRED`
- `VAT.NET_NOT_POSITIVE`
- `VAT.NEGATIVE_VAT`

Additional route-level HTTP errors are also used (for example forbidden role checks or export failures).

## Cross-Domain Integration

- `businesses`: validates business existence/status and enriches with business display/status.
- `users/auth`: all VAT endpoints use current-user dependency; advisor-only operations enforce role checks.
- `annual_reports`: reuses shared `SubmissionMethod` enum (`online` / `manual` / `representative`).

## Tests

VAT reports test suites:
- `tests/vat_reports/api/test_vat_reports_intake.py`
- `tests/vat_reports/api/test_vat_reports_invoices.py`
- `tests/vat_reports/api/test_vat_reports_invoices_update_and_filters.py`
- `tests/vat_reports/api/test_vat_reports_materials_complete.py`
- `tests/vat_reports/api/test_vat_reports_queries.py`
- `tests/vat_reports/api/test_vat_reports_status.py`
- `tests/vat_reports/api/test_vat_reports_filing.py`
- `tests/vat_reports/api/test_vat_reports_audit.py`
- `tests/vat_reports/api/test_vat_client_summary_export.py`
- `tests/vat_reports/api/test_vat_reports_utils.py`
- `tests/vat_reports/service/test_vat_report_intake.py`
- `tests/vat_reports/service/test_vat_report_invoices.py`
- `tests/vat_reports/service/test_data_entry_service_additional.py`
- `tests/vat_reports/service/test_vat_report_queries.py`
- `tests/vat_reports/service/test_vat_report_status_transitions.py`
- `tests/vat_reports/service/test_vat_report_service_queries.py`
- `tests/vat_reports/service/test_vat_export_pdf_functions.py`
- `tests/vat_reports/service/test_vat_report_test_utils.py`
- `tests/vat_reports/repository/test_vat_client_summary_repository.py`
- `tests/vat_reports/repository/test_vat_work_item_repository.py`
- `tests/vat_reports/repository/test_vat_invoice_repository.py`

Run only this domain:

```bash
pytest tests/vat_reports -q
```
