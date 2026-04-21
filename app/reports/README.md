# Reports Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages management/operational reports and exports (aging, VAT compliance, advance-payments collections, annual-report status).

## Scope

This module provides:
- Aging report for unpaid issued charges
- Aging export to Excel/PDF
- VAT compliance report by year
- Advance-payments collections report by year/month
- Annual-reports status report by tax year
- Role-based API access (advisor only)

## Domain Model

This module currently does not define its own persistent domain tables.

Reports are computed from other domains and returned as derived payloads through `app/reports/schemas.py` response models:
- Aging report payload (`report_date`, `items`, `summary`, `capped`, etc.)
- VAT compliance payload (`items`, `stale_pending`)
- Advance-payment collections payload (`collection_rate`, `items`, etc.; client-scoped aggregates)
- Annual-report status payload (`statuses[]` grouped by annual-report status)

Implementation references:
- API: `app/reports/api/reports.py`
- Constants: `app/reports/constants.py`
- Schemas: `app/reports/schemas.py`
- Services:
  - `app/reports/services/reports_service.py`
  - `app/reports/services/vat_compliance_report.py`
  - `app/reports/services/advance_payment_report.py`
  - `app/reports/services/annual_report_status_report.py`
  - `app/reports/services/export_service.py`
  - `app/reports/services/export_excel.py`
  - `app/reports/services/export_pdf.py`

## API

Router prefix is `/api/v1/reports` (mounted in `app/router_registry.py`).

All endpoints require role: `ADVISOR`.

### VAT compliance report
- `GET /api/v1/reports/vat-compliance`
- Query params:
  - `year` (required)
- `stale_pending` includes only items from the requested year.

### Advance-payments collections report
- `GET /api/v1/reports/advance-payments`
- Query params:
  - `year` (required)
  - `month` (optional)
- Aggregation is client-scoped and returns `client_id` / `client_name` per row.

### Annual-reports status report
- `GET /api/v1/reports/annual-reports`
- Query params:
  - `tax_year` (required)

### Aging report
- `GET /api/v1/reports/aging`
- Query params:
  - `as_of_date` (optional; defaults to today)

Returns bucketed outstanding debt:
- `current` (0-30)
- `days_30` (31-60)
- `days_60` (61-90)
- `days_90_plus` (91+)

### Aging export
- `GET /api/v1/reports/aging/export`
- Query params:
  - `format` (required: `excel|pdf`)
  - `as_of_date` (optional)

Returns downloadable file (`FileResponse`):
- Excel: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- PDF: `application/pdf`

## Behavior Notes

- Aging report considers only charges with status `issued` and a non-null `issued_at`.
- Aging report applies an in-memory cap for unpaid charges:
  - `AGING_CHARGE_FETCH_LIMIT = 2000`
  - response includes:
    - `capped` (`true` when total unpaid exceeds cap)
    - `cap_limit` (current cap)
- Aging items are sorted by `total_outstanding` descending.
- Export service writes generated files to temp export directory (`/tmp/.../exports`) and returns file metadata/path.
- Excel export requires `openpyxl`; PDF export requires `reportlab`.
- Export endpoint converts missing export libs to `500` with explicit install guidance.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Reports export endpoint may return route-level HTTP errors for:
- Invalid format values
- Missing export dependencies
- Unexpected export failures

## Cross-Domain Integration

Reports aggregate from:
- `charge` (aging, unpaid issued charges)
- `clients` (client names/counts)
- `vat_reports` (VAT compliance by period/status)
- `advance_payments` (collections/gap metrics)
- `annual_reports` (status grouping and filing deadlines)

## Tests

Reports test suites:
- `tests/reports/api/test_reports_aging.py`
- `tests/reports/api/test_reports_aging_export.py`
- `tests/reports/api/test_reports_additional_endpoints.py`
- `tests/reports/api/test_reports_export_errors.py`
- `tests/reports/service/test_reports_service_and_exports.py`

Related regression coverage:
- `tests/regression/test_reports_export_manual.py`

Run only this domain:

```bash
pytest tests/reports -q
```
