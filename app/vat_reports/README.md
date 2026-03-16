# VAT Reports Module

Manages VAT work-item lifecycle (intake, data entry, review, filing), invoice capture, audit trail, and client-level summary/export.

## Scope

This module provides:
- VAT work-item creation per client/period
- Lifecycle status transitions from intake to filed state
- Invoice add/list/delete flows with totals recalculation
- Advisor filing flow with optional override + justification
- Work-item and audit-trail query endpoints with pagination
- Client VAT summary endpoint and yearly export (Excel/PDF)

## Domain Model

`VatWorkItem` fields:
- `id` (PK)
- `client_id` (FK, required)
- `created_by` (FK, required)
- `assigned_to` (FK, optional)
- `period` (`YYYY-MM`, required)
- `status` (enum)
- `pending_materials_note` (optional)
- `total_output_vat`, `total_input_vat`, `net_vat`
- `final_vat_amount` (optional)
- `is_overridden` (boolean)
- `override_justification` (optional)
- `filing_method` (enum, optional)
- `filed_at`, `filed_by` (optional)
- `created_at`, `updated_at`

Uniqueness:
- one work item per (`client_id`, `period`)

`VatInvoice` fields:
- `id` (PK)
- `work_item_id` (FK, required)
- `created_by` (FK, required)
- `invoice_type` (enum)
- `invoice_number` (required)
- `invoice_date` (required)
- `counterparty_name` (required)
- `counterparty_id` (optional)
- `net_amount`, `vat_amount`
- `expense_category` (optional enum; required for expense invoices)
- `created_at`

Invoice uniqueness:
- one invoice number per (`work_item_id`, `invoice_type`, `invoice_number`)

`VatAuditLog` fields:
- `id` (PK)
- `work_item_id` (FK)
- `performed_by` (FK)
- `action`
- `old_value`, `new_value`, `note`
- `performed_at`

Status enum values:
- `pending_materials`
- `material_received`
- `data_entry_in_progress`
- `ready_for_review`
- `filed`

Additional enums:
- Filing method: `manual`, `online`
- Invoice type: `income`, `expense`
- Expense category: `office`, `travel`, `professional_services`, `equipment`, `rent`, `salary`, `marketing`, `other`

Implementation references:
- Models: `app/vat_reports/models/vat_work_item.py`, `app/vat_reports/models/vat_invoice.py`, `app/vat_reports/models/vat_audit_log.py`, `app/vat_reports/models/vat_enums.py`
- Schemas: `app/vat_reports/schemas/vat_report.py`, `app/vat_reports/schemas/vat_client_summary_schema.py`
- Repositories: `app/vat_reports/repositories/vat_work_item_repository.py`, `app/vat_reports/repositories/vat_invoice_repository.py`, `app/vat_reports/repositories/vat_client_summary_repository.py`
- Services: `app/vat_reports/services/vat_report_service.py` and delegated flows under `app/vat_reports/services/`
- API: `app/vat_reports/api/routers.py` + route files in `app/vat_reports/api/`

## API

Router prefix is `/api/v1/vat` (mounted in `app/main.py` via `vat_reports_router`).

### Create work item
- `POST /api/v1/vat/work-items`
- Requires authenticated user
- Body:

```json
{
  "client_id": 123,
  "period": "2026-01",
  "assigned_to": 45,
  "mark_pending": true,
  "pending_materials_note": "Missing bank statement"
}
```

### Mark materials complete
- `POST /api/v1/vat/work-items/{item_id}/materials-complete`
- Requires authenticated user
- Transition: `pending_materials -> material_received`

### Add invoice
- `POST /api/v1/vat/work-items/{item_id}/invoices`
- Requires authenticated user
- Body (example):

```json
{
  "invoice_type": "expense",
  "invoice_number": "INV-1001",
  "invoice_date": "2026-01-15T00:00:00Z",
  "counterparty_name": "Vendor Ltd",
  "counterparty_id": "512345678",
  "net_amount": 1000,
  "vat_amount": 170,
  "expense_category": "office"
}
```

### List invoices
- `GET /api/v1/vat/work-items/{item_id}/invoices`
- Requires authenticated user
- Query params:
  - `invoice_type` (optional: `income` or `expense`)

### Delete invoice
- `DELETE /api/v1/vat/work-items/{item_id}/invoices/{invoice_id}`
- Requires authenticated user
- Returns `204 No Content`

### Mark ready for review
- `POST /api/v1/vat/work-items/{item_id}/ready-for-review`
- Requires authenticated user
- Transition: `data_entry_in_progress -> ready_for_review`

### Send back for correction
- `POST /api/v1/vat/work-items/{item_id}/send-back`
- Role: `ADVISOR`
- Body:

```json
{
  "correction_note": "Please fix invoice classification"
}
```

- Transition: `ready_for_review -> data_entry_in_progress`

### File VAT return
- `POST /api/v1/vat/work-items/{item_id}/file`
- Role: `ADVISOR`
- Body:

```json
{
  "filing_method": "online",
  "override_amount": 2500,
  "override_justification": "Authority correction per call"
}
```

### Get work item
- `GET /api/v1/vat/work-items/{item_id}`
- Requires authenticated user

### List client work items
- `GET /api/v1/vat/clients/{client_id}/work-items`
- Requires authenticated user

### List work items
- `GET /api/v1/vat/work-items`
- Requires authenticated user
- Query params:
  - `status` (optional)
  - `page` (default `1`, min `1`)
  - `page_size` (default `50`, min `1`, max `200`)

### Get work-item audit trail
- `GET /api/v1/vat/work-items/{item_id}/audit`
- Requires authenticated user

### Client summary
- `GET /api/v1/vat/client/{client_id}/summary`
- Roles: `ADVISOR`, `SECRETARY`

### Client export
- `GET /api/v1/vat/client/{client_id}/export`
- Role: `ADVISOR`
- Query params:
  - `format` (`excel` or `pdf`)
  - `year` (2000-2100)

## Behavior Notes

- Work-item period must be `YYYY-MM`.
- Creating duplicate work item for same (`client_id`, `period`) is rejected.
- If `mark_pending=true`, `pending_materials_note` is required.
- First invoice on a `material_received` item auto-transitions it to `data_entry_in_progress`.
- Editing is blocked once item status is `filed`.
- Expense invoices require `expense_category`.
- `net_amount` must be positive; `vat_amount` must be non-negative.
- `ready_for_review` and filing transitions enforce strict state checks.
- Filing override requires explicit justification.
- Invoice mutations trigger totals recalculation (`output`, `input`, `net`) and append audit entries.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

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

- `clients`: validates client existence and enriches responses with client names.
- `users/auth`: all VAT endpoints use current-user dependency; advisor-only operations enforce role checks.
- `reports`: VAT client summary and export endpoints provide reporting outputs (Excel/PDF).

## Tests

VAT reports test suites:
- `tests/vat_reports/api/test_vat_reports_intake.py`
- `tests/vat_reports/api/test_vat_reports_invoices.py`
- `tests/vat_reports/api/test_vat_reports_status.py`
- `tests/vat_reports/api/test_vat_reports_filing.py`
- `tests/vat_reports/api/test_vat_reports_audit.py`
- `tests/vat_reports/api/test_vat_client_summary_export.py`
- `tests/vat_reports/api/test_vat_reports_utils.py`
- `tests/vat_reports/service/test_vat_report_intake.py`
- `tests/vat_reports/service/test_vat_report_invoices.py`
- `tests/vat_reports/service/test_vat_report_status_transitions.py`
- `tests/vat_reports/service/test_vat_report_service_queries.py`
- `tests/vat_reports/service/test_vat_export_pdf_functions.py`
- `tests/vat_reports/service/test_vat_report_test_utils.py`
- `tests/vat_reports/repository/test_vat_work_item_repository.py`
- `tests/vat_reports/repository/test_vat_invoice_repository.py`

Run only this domain:

```bash
pytest tests/vat_reports -q
```
