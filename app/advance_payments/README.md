# Advance Payments Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages client advance tax-payment records (monthly prepayments), schedule generation, overview analytics, and KPI/chart endpoints.

## Scope

This module provides:
- CRUD operations for client advance payments
- Filtering + pagination for client-year payment lists
- Bulk annual schedule generation (12 months, idempotent)
- Expected amount suggestion based on prior-year VAT + tax profile rate
- Overview table + KPI aggregation endpoints
- Annual and monthly chart/KPI endpoints per client

## Domain Model

`AdvancePayment` fields:
- `id` (PK)
- `client_id` (FK, required)
- `tax_deadline_id` (optional FK)
- `annual_report_id` (optional FK)
- `month` (1-12, required)
- `year` (required)
- `expected_amount` (optional)
- `paid_amount` (optional)
- `status` (enum, default `pending`)
- `due_date` (required)
- `notes` (optional, max 500)
- `created_at`, `updated_at`

Uniqueness:
- one row per (`client_id`, `year`, `month`)

Status enum values:
- `pending`
- `paid`
- `partial`
- `overdue`

Implementation references:
- Model: `app/advance_payments/models/advance_payment.py`
- Schemas: `app/advance_payments/schemas/advance_payment.py`
- Repositories: `app/advance_payments/repositories/advance_payment_repository.py`, `app/advance_payments/repositories/advance_payment_analytics_repository.py`
- Services: `app/advance_payments/services/advance_payment_service.py`, `app/advance_payments/services/advance_payment_generator.py`, `app/advance_payments/services/advance_payment_calculator.py`
- API: `app/advance_payments/api/advance_payments.py`, `app/advance_payments/api/advance_payment_generate.py`, `app/advance_payments/api/advance_payments_overview.py`

## API

Router prefix is `/api/v1/advance-payments` (mounted in `app/main.py`).

### List advance payments
- `GET /api/v1/advance-payments`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (required)
  - `year` (optional; defaults to current year)
  - `status` (optional repeatable enum filter)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

### Create advance payment
- `POST /api/v1/advance-payments`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_id": 123,
  "year": 2026,
  "month": 3,
  "due_date": "2026-03-15",
  "expected_amount": 2500.0,
  "paid_amount": 0,
  "tax_deadline_id": 15,
  "notes": "First quarter prepayment"
}
```

### Suggest expected amount
- `GET /api/v1/advance-payments/suggest`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (required)
  - `year` (required)

### Update advance payment
- `PATCH /api/v1/advance-payments/{payment_id}`
- Role: `ADVISOR` only
- Allowed fields: `paid_amount`, `expected_amount`, `status`, `notes`

### Delete advance payment
- `DELETE /api/v1/advance-payments/{payment_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

### Generate annual schedule
- `POST /api/v1/advance-payments/generate`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_id": 123,
  "year": 2026
}
```

- Returns created/skipped counts.

### Overview list + KPIs
- `GET /api/v1/advance-payments/overview`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `year` (required)
  - `month` (optional, 1-12)
  - `status` (optional repeatable string values)
  - `page` (default `1`, min `1`)
  - `page_size` (default `50`, min `1`, max `200`)

### Monthly chart data
- `GET /api/v1/advance-payments/chart`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (required)
  - `year` (required)

### Annual KPIs
- `GET /api/v1/advance-payments/kpi`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (required)
  - `year` (required)

## Behavior Notes

- Payment creation validates client existence and enforces unique (`client_id`, `year`, `month`).
- Update endpoint accepts only whitelisted fields (`paid_amount`, `expected_amount`, `status`, `notes`).
- Empty update payload is rejected by schema validation.
- Annual schedule generation is idempotent:
  - loops months 1-12
  - skips months that already exist
  - default due date is the 15th of each month
- Suggestion endpoint returns `None` when either:
  - client tax profile/advance rate is missing, or
  - prior-year VAT output data is missing.
- Suggestion formula:
  - derive annual income from prior-year output VAT
  - apply advance rate
  - divide by 12 and round to nearest whole shekel

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `ADVANCE_PAYMENT.NOT_FOUND`
- `ADVANCE_PAYMENT.CLIENT_NOT_FOUND`
- `ADVANCE_PAYMENT.CONFLICT`
- `ADVANCE_PAYMENT.RATE_INVALID`
- `CLIENT.NOT_FOUND`

Additional route-specific HTTP and validation errors are also used.

## Cross-Domain Integration

- `clients`: validates client existence and enriches overview rows with client names.
- `clients/tax profile`: suggestion flow reads `advance_rate` from client tax profile.
- `vat_reports`: suggestion flow uses prior-year VAT output totals.
- `tax_deadline`: optional FK (`tax_deadline_id`) can link prepayments to tax deadlines.
- `annual_reports`: optional FK (`annual_report_id`) can link prepayments to annual report context.

## Tests

Advance payments test suites:
- `tests/advance_payments/api/test_advance_payments.py`
- `tests/advance_payments/api/test_advance_payments_create_overview.py`
- `tests/advance_payments/api/test_advance_payments_delete.py`
- `tests/advance_payments/api/test_advance_payments_kpi_chart.py`
- `tests/advance_payments/repository/test_advance_payment_repository.py`
- `tests/advance_payments/service/test_advance_payment.py`
- `tests/advance_payments/service/test_advance_payment_create_success.py`
- `tests/advance_payments/service/test_advance_payment_overview_kpis.py`

Run only this domain:

```bash
pytest tests/advance_payments -q
```
