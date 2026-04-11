# Advance Payments Module

> Last audited: 2026-04-11

Manages advance tax-payment records (מקדמות) per client per period, schedule generation, overview analytics, and KPI/chart endpoints.

## Scope

This module provides:
- CRUD operations for client advance payments
- Filtering + pagination for client-year payment lists
- Bulk annual schedule generation (idempotent, monthly or bi-monthly)
- Expected amount suggestion based on prior-year VAT + tax profile rate
- Overview table + KPI aggregation endpoints
- Annual and monthly chart/KPI endpoints per client

## Domain Model

`AdvancePayment` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `annual_report_id` (optional FK -> `annual_reports.id`)
- `period` (`YYYY-MM`, required) — first month of the reporting period
- `period_months_count` (1=monthly, 2=bi-monthly, required)
- `due_date` (required)
- `expected_amount` (optional)
- `paid_amount` (optional)
- `status` (enum, default `pending`)
- `paid_at` (optional)
- `payment_method` (enum, optional)
- `notes` (optional, max 500)
- `created_at`, `updated_at`
- `deleted_at`, `deleted_by` (soft delete)

Uniqueness:
- one row per (`client_id`, `period`)

Status enum values:
- `pending`
- `paid`
- `partial`
- `overdue`

Payment method enum values:
- `bank_transfer`
- `credit_card`
- `check`
- `direct_debit`
- `cash`
- `other`

Implementation references:
- Model: `app/advance_payments/models/advance_payment.py`
- Schemas: `app/advance_payments/schemas/advance_payment.py`
- Repositories: `app/advance_payments/repositories/advance_payment_repository.py`, `app/advance_payments/repositories/advance_payment_analytics_repository.py`
- Services: `app/advance_payments/services/advance_payment_service.py`, `app/advance_payments/services/advance_payment_generator.py`, `app/advance_payments/services/advance_payment_calculator.py`
- API: `app/advance_payments/api/advance_payments.py`, `app/advance_payments/api/advance_payment_generate.py`, `app/advance_payments/api/advance_payments_overview.py`

## API

Routers are mounted in `app/main.py` under `/api/v1`.

### Client-scoped endpoints (`/api/v1/clients/{client_id}/advance-payments`)

Roles: `ADVISOR`, `SECRETARY`

#### List advance payments
- `GET /api/v1/clients/{client_id}/advance-payments`
- Query params:
  - `year` (optional; defaults to current year)
  - `status` (optional repeatable enum filter)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

#### Create advance payment
- `POST /api/v1/clients/{client_id}/advance-payments`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_id": 123,
  "period": "2026-03",
  "period_months_count": 1,
  "due_date": "2026-04-15",
  "expected_amount": 2500.00,
  "paid_amount": null,
  "payment_method": "direct_debit",
  "annual_report_id": null,
  "notes": "מקדמה חודשית מרץ"
}
```

#### Suggest expected amount
- `GET /api/v1/clients/{client_id}/advance-payments/suggest`
- Query params:
  - `year` (required)

#### Annual KPIs
- `GET /api/v1/clients/{client_id}/advance-payments/kpi`
- Query params:
  - `year` (required)

#### Monthly chart data
- `GET /api/v1/clients/{client_id}/advance-payments/chart`
- Query params:
  - `year` (required)

#### Update advance payment
- `PATCH /api/v1/clients/{client_id}/advance-payments/{payment_id}`
- Role: `ADVISOR` only
- Allowed fields: `paid_amount`, `expected_amount`, `status`, `paid_at`, `payment_method`, `notes`

#### Delete advance payment
- `DELETE /api/v1/clients/{client_id}/advance-payments/{payment_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

### Standalone endpoints (`/api/v1/advance-payments`)

#### Generate annual schedule
- `POST /api/v1/clients/{client_id}/advance-payments/generate`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_id": 123,
  "year": 2026,
  "period_months_count": 1
}
```

- Returns `{"created": N, "skipped": N}`
- Idempotent — skips periods that already exist.

#### Overview list + KPIs
- `GET /api/v1/advance-payments/overview`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `year` (required)
  - `month` (optional, 1-12)
  - `status` (optional repeatable string values)
  - `page` (default `1`, min `1`)
  - `page_size` (default `50`, min `1`, max `200`)

## Behavior Notes

- Payment creation validates client existence and status (`CLOSED`/`FROZEN` blocked).
- Uniqueness enforced on (`client_id`, `period`) — duplicate raises `ADVANCE_PAYMENT.CONFLICT`.
- Update endpoint accepts only whitelisted fields.
- Empty update payload is rejected by schema validation.
- Annual schedule generation:
  - `period_months_count=1`: 12 monthly periods (`YYYY-01` … `YYYY-12`)
  - `period_months_count=2`: 6 bi-monthly periods (`YYYY-01`, `YYYY-03`, `YYYY-05`, …)
  - `due_date` = 15th of the month following the period end
  - Skips periods that already exist (idempotent)
- Suggestion formula:
  - Reads `advance_rate` from client tax profile
  - Reads prior-year output VAT from `VatClientSummaryRepository`
  - `annual_income = output_vat / 0.18`
  - `monthly = (annual_income × rate / 100) / 12`, rounded to nearest shekel
  - Returns `None` when rate or prior-year VAT data is missing

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

## Cross-Domain Integration

- `clients`: validates client existence and status before create.
- `vat_reports`: suggestion flow uses prior-year output VAT totals via `VatClientSummaryRepository`.
- `annual_reports`: optional FK (`annual_report_id`) links a payment to an annual report.

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
