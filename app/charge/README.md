# Charges Module

Manages client billing charges (draft, issue, payment, cancellation) used by the CRM and referenced by related operational domains.

## Scope

This module provides:
- CRUD-like lifecycle for `charges` (create, read, status transitions, soft delete)
- Filtering + pagination by client/status/type
- Role-based API access and role-based response shaping
- Bulk charge actions (`issue`, `mark-paid`, `cancel`)
- Soft delete with audit fields (`deleted_at`, `deleted_by`)

## Domain Model

`Charge` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `amount` (required)
- `currency` (default `ILS`)
- `charge_type` (enum, required)
- `period` (optional, `YYYY-MM`)
- `status` (enum, default `draft`)
- `created_at`, `issued_at`, `paid_at`
- `created_by`, `issued_by`, `paid_by`, `canceled_by`
- `canceled_at`, `cancellation_reason`
- `annual_report_id` (optional FK -> `annual_reports.id`)
- `deleted_at`, `deleted_by` (for soft delete)

Charge type enum values:
- `retainer`
- `one_time`

Charge status enum values:
- `draft`
- `issued`
- `paid`
- `canceled`

Implementation references:
- Model: `app/charge/models/charge.py`
- Schemas: `app/charge/schemas/charge.py`
- Repository: `app/charge/repositories/charge_repository.py`
- Services: `app/charge/services/billing_service.py`, `app/charge/services/bulk_billing_service.py`
- API: `app/charge/api/charge.py`

## API

Router prefix is `/api/v1/charges` (mounted in `app/main.py`).

### Create charge
- `POST /api/v1/charges`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_id": 123,
  "amount": 100.0,
  "charge_type": "one_time",
  "period": "2026-03",
  "currency": "ILS"
}
```

### List charges
- `GET /api/v1/charges`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (optional)
  - `status` (optional)
  - `charge_type` (optional)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

### Get charge
- `GET /api/v1/charges/{charge_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Response shape depends on role:
  - Advisor: full `ChargeResponse`
  - Secretary: `ChargeResponseSecretary` (without financial amount/currency)

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

- Creating a charge validates that the client exists (`CLIENT.NOT_FOUND` on missing client).
- Amount must be positive (`CHARGE.AMOUNT_INVALID` on invalid amount).
- Lifecycle rules:
  - Only `draft` can be issued.
  - Only `issued` can be marked paid.
  - `draft`/`issued` can be canceled.
  - `paid` cannot be canceled.
  - Canceling an already canceled charge returns `CHARGE.CONFLICT`.
- Delete is only allowed for `draft` charges; other statuses return `CHARGE.INVALID_STATUS`.
- Repository reads (`get_by_id`, list/count) exclude soft-deleted records.
- Issuing a charge triggers an unpaid-charge reminder creation.
- Bulk action is partial-success by design: failures are reported per item and do not abort successful items.

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
- `CLIENT.NOT_FOUND`

## Cross-Domain Integration

- `reminders` integration: issuing a charge creates an unpaid-charge reminder (`ReminderService.create_unpaid_charge_reminder`).
- `actions` integration: charge actions are exposed via `app/actions/action_contracts.py` for executable UI actions.
- `dashboard` and other domains can query charge counts/status through `ChargeRepository`.

## Tests

Charge test suites:
- `tests/charge/api/test_charges_api_authorization.py`
- `tests/charge/api/test_charges_api_lifecycle.py`
- `tests/charge/api/test_authorization_refinement.py`
- `tests/charge/repository/test_charge_repository.py`
- `tests/regression/test_core_regressions_binders_charges_notifications.py`

Run only this domain:

```bash
pytest tests/charge tests/regression/test_core_regressions_binders_charges_notifications.py -q
```
