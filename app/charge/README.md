# Charges Module

> Last audited: 2026-03-22 (post-refactor sync).

Manages client billing charges (draft, issue, payment, cancellation) used by the CRM and referenced by related operational domains.

## Scope

This module provides:
- CRUD-like lifecycle for `charges` (create, read, status transitions, soft delete)
- Filtering + pagination by client/business/status/type
- Role-based API access and role-based response shaping
- Bulk charge actions (`issue`, `mark-paid`, `cancel`) with idempotency key enforcement
- Soft delete with audit fields (`deleted_at`, `deleted_by`)

## Domain Model

`Charge` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required, source of truth)
- `business_id` (FK -> `businesses.id`, optional, operational affiliation only)
- `annual_report_id` (optional FK -> `annual_reports.id`)
- `charge_type` (enum, required)
- `status` (enum, default `draft`)
- `amount` (required, always ILS)
- `period` (optional, `YYYY-MM` — first month of the billing period)
- `months_covered` (default `1`)
- `description` (optional)
- `created_at`, `issued_at`, `paid_at`
- `created_by`, `issued_by`, `paid_by`, `canceled_by`
- `canceled_at`, `cancellation_reason`
- `deleted_at`, `deleted_by` (soft delete)

Charge type enum values:
- `monthly_retainer`
- `annual_report_fee`
- `vat_filing_fee`
- `representation_fee`
- `consultation_fee`
- `other`

Charge status enum values:
- `draft`
- `issued`
- `paid`
- `canceled`

Implementation references:
- Model: `app/charge/models/charge.py`
- Schemas: `app/charge/schemas/charge.py`
- Repository: `app/charge/repositories/charge_repository.py`
- Services:
  - `app/charge/services/billing_service.py` — lifecycle mutations (create, issue, mark-paid, cancel, delete)
  - `app/charge/services/charge_query_service.py` — read operations, enrichment, role-shaped listing
  - `app/charge/services/bulk_billing_service.py` — bulk action orchestration
- API: `app/charge/api/charge.py`

## Service Architecture

The service layer is split into two classes:

| Class | File | Responsibility |
|---|---|---|
| `BillingService` | `billing_service.py` | Lifecycle mutations — create, issue, mark-paid, cancel, delete, get |
| `ChargeQueryService` | `charge_query_service.py` | Read operations — list, count, business-name enrichment, role-shaped responses |
| `BulkBillingService` | `bulk_billing_service.py` | Partial-success bulk action loop over `BillingService` |

All API route handlers import both `BillingService` and `ChargeQueryService` directly. `BulkBillingService` wraps `BillingService` only.

## API

Router prefix is `/api/v1/charges` (mounted in `app/main.py`).

### Create charge
- `POST /api/v1/charges`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_id": 456,
  "business_id": 123,
  "amount": 1500.00,
  "charge_type": "monthly_retainer",
  "period": "2026-03",
  "months_covered": 1,
  "description": "Optional free-text label"
}
```

### List charges
- `GET /api/v1/charges`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `business_id` (optional)
  - `client_id` (optional)
  - `status` (optional)
  - `charge_type` (optional)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)
- Response shape depends on role:
  - Advisor: full `ChargeResponse` (includes `amount`, financial timestamps)
  - Secretary: `ChargeResponseSecretary` (omits `amount` and financial fields)

### Get charge
- `GET /api/v1/charges/{charge_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Same role-based response shaping as list.

### Issue charge
- `POST /api/v1/charges/{charge_id}/issue`
- Role: `ADVISOR` only

### Mark charge as paid
- `POST /api/v1/charges/{charge_id}/mark-paid`
- Role: `ADVISOR` only

### Cancel charge
- `POST /api/v1/charges/{charge_id}/cancel`
- Role: `ADVISOR` only
- Optional body:

```json
{
  "reason": "optional cancellation reason"
}
```

### Bulk action
- `POST /api/v1/charges/bulk-action`
- Role: `ADVISOR` only
- Required header: `X-Idempotency-Key`
- Body:

```json
{
  "charge_ids": [1, 2, 3],
  "action": "issue",
  "cancellation_reason": "optional"
}
```

`action` values:
- `issue`
- `mark-paid`
- `cancel`

### Delete charge (soft delete)
- `DELETE /api/v1/charges/{charge_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

## Behavior Notes

- Creating a charge validates that the client exists. If `business_id` is provided, it must belong to that client and must not be closed/frozen (`CHARGE.CLIENT_NOT_FOUND`, `CHARGE.BUSINESS_CLIENT_MISMATCH`, `BUSINESS.NOT_FOUND`, `BUSINESS.CLOSED`, `BUSINESS.FROZEN`).
- Amount must be positive (`CHARGE.AMOUNT_INVALID` on invalid amount). All charges are always in ILS — no currency field.
- Lifecycle rules:
  - Only `draft` can be issued.
  - Only `issued` can be marked paid.
  - `draft`/`issued` can be canceled.
  - `paid` cannot be canceled.
  - Canceling an already canceled charge returns `CHARGE.CONFLICT`.
- Delete is only allowed for `draft` charges; other statuses return `CHARGE.INVALID_STATUS`.
- Repository reads (`get_by_id`, list/count) exclude soft-deleted records.
- Issuing a charge auto-creates an unpaid-charge reminder via `ReminderService.create_unpaid_charge_reminder`.
- `get_charge` in `BillingService` raises `NotFoundError` (never returns `None`).
- Bulk action is partial-success by design: `AppError` failures surface `exc.message`; unexpected errors return a generic Hebrew fallback. Neither aborts remaining items.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `CHARGE.NOT_FOUND`
- `CHARGE.INVALID_STATUS`
- `CHARGE.CONFLICT`
- `CHARGE.AMOUNT_INVALID`
- `BUSINESS.NOT_FOUND`
- `BUSINESS.CLOSED`
- `BUSINESS.FROZEN`

## Cross-Domain Integration

- `reminders` integration: issuing a charge creates an unpaid-charge reminder (`ReminderService.create_unpaid_charge_reminder`).
- `actions` integration: charge actions are exposed via `app/actions/action_contracts.py` for executable UI actions.
- `dashboard` and other domains query charge counts/status through `ChargeRepository` directly.
- `invoice` integration: `InvoiceService` validates charge existence and `issued` status before attaching an external invoice reference.
- `annual_reports` integration: optional `annual_report_id` FK links a charge to a specific annual report.

## Tests

Charge test suites (`tests/charge`):
- `tests/charge/api/test_charges_api_authorization.py`
- `tests/charge/api/test_charges_api_lifecycle.py`
- `tests/charge/api/test_charges_api_additional.py`
- `tests/charge/api/test_authorization_refinement.py`
- `tests/charge/repository/test_charge_repository.py`
- `tests/charge/service/test_billing_service_additional.py`
- `tests/charge/service/test_bulk_billing_service.py`

Cross-domain regression coverage that includes charge flows:
- `tests/regression/test_core_regressions_binders_charges_notifications.py`

Run only this domain:

```bash
pytest tests/charge tests/regression/test_core_regressions_binders_charges_notifications.py -q
```
