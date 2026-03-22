# Reminders Module

> Last audited: 2026-03-22

Manages proactive reminder scheduling and lifecycle (`pending` / `sent` / `canceled`) for business-related events such as tax deadlines, VAT filing, annual reports, advance payments, idle binders, unpaid charges, missing documents, and custom reminders.

## Scope

This module provides:
- Reminder creation for all supported reminder types
- Pending reminders listing by `send_on <= today`
- Business-scoped reminder listing
- Status-scoped reminder listing
- Reminder retrieval by id
- Reminder status transitions (`pending -> sent` / `pending -> canceled`)
- Role-based API access

## Domain Model

`Reminder` fields:
- `id` (PK)
- `business_id` (FK -> `businesses.id`, required)
- `reminder_type` (enum, required)
- `status` (enum, default `pending`)
- `target_date` (required)
- `days_before` (required)
- `send_on` (precomputed send date)
- `message` (required)
- Optional domain references:
  - `binder_id` (FK -> `binders.id`)
  - `charge_id` (FK -> `charges.id`)
  - `tax_deadline_id` (FK -> `tax_deadlines.id`)
  - `annual_report_id` (FK -> `annual_reports.id`)
  - `advance_payment_id` (FK -> `advance_payments.id`)
- Lifecycle and metadata:
  - `created_at`, `sent_at`, `canceled_at`
  - `created_by`, `canceled_by`
- Soft delete:
  - `deleted_at`, `deleted_by`

Reminder type enum values:
- `tax_deadline_approaching`
- `vat_filing`
- `advance_payment_due`
- `annual_report_deadline`
- `binder_idle`
- `unpaid_charge`
- `document_missing`
- `custom`

Reminder status enum values:
- `pending`
- `sent`
- `canceled`

Implementation references:
- Model: `app/reminders/models/reminder.py`
- Schemas: `app/reminders/schemas/reminders.py`
- Repository: `app/reminders/repositories/reminder_repository.py`
- Services: `app/reminders/services/reminder_service.py`, `app/reminders/services/factory.py`, `app/reminders/services/factory_extended.py`, `app/reminders/services/reminder_queries.py`, `app/reminders/services/status_changes.py`
- API routers: `app/reminders/api/routers.py` + route modules in `app/reminders/api/`

## API

Router is mounted as `/api/v1/reminders` (registered in `app/router_registry.py`).

Base access: `ADVISOR` or `SECRETARY`.

Endpoint-specific access:
- `POST /api/v1/reminders/` -> `ADVISOR` only
- `GET /api/v1/reminders/` -> `ADVISOR`, `SECRETARY`
- `GET /api/v1/reminders/{reminder_id}` -> `ADVISOR`, `SECRETARY`
- `POST /api/v1/reminders/{reminder_id}/cancel` -> `ADVISOR`, `SECRETARY`
- `POST /api/v1/reminders/{reminder_id}/mark-sent` -> `ADVISOR`, `SECRETARY`

### Create reminder

Body (`ReminderCreateRequest`) uses `business_id` (not `client_id`):

```json
{
  "business_id": 123,
  "reminder_type": "custom",
  "target_date": "2026-03-30",
  "days_before": 3,
  "message": "Reminder text"
}
```

Type-specific required fields:
- `binder_idle` -> requires `binder_id`
- `unpaid_charge` -> requires `charge_id`
- `tax_deadline_approaching` or `vat_filing` -> requires `tax_deadline_id`
- `annual_report_deadline` -> requires `annual_report_id`
- `advance_payment_due` -> requires `advance_payment_id`
- `custom` and `document_missing` -> require non-empty `message`

### List reminders

`GET /api/v1/reminders/`

Query params:
- `status` (optional: `pending|sent|canceled`)
- `business_id` (optional)
- `page` (default `1`, min `1`)
- `page_size` (default `20`, min `1`, max `100`)

Behavior:
- If `business_id` is provided, returns reminders for that business (all statuses).
- Otherwise:
  - if `status` is provided: returns reminders by that status.
  - if `status` is omitted: returns pending reminders with `send_on <= today`.

List/get responses are enriched with `business_name`.

### Get reminder

`GET /api/v1/reminders/{reminder_id}`

Returns one reminder or 404.

### Cancel reminder

`POST /api/v1/reminders/{reminder_id}/cancel`

Valid only from `pending`.

### Mark reminder as sent

`POST /api/v1/reminders/{reminder_id}/mark-sent`

Valid only from `pending`.

## Behavior Notes

- Creation validates referenced entities:
  - Business must exist.
  - Tax deadline / binder / charge / annual report / advance payment must exist when relevant.
- Scheduling logic:
  - Deadline-style reminders (`tax_deadline_approaching`, `vat_filing`, `annual_report_deadline`, `advance_payment_due`, `custom`, `document_missing`):
    - `send_on = target_date - days_before`
  - `binder_idle`:
    - `target_date = today + days_idle`
    - `send_on = today`
    - stored `days_before = 0`
  - `unpaid_charge`:
    - `target_date = today`
    - `send_on = today`
    - stored `days_before = 0`
- Negative day values are rejected (`REMINDER.NEGATIVE_DAYS`).
- Invalid status filter is rejected (`REMINDER.INVALID_STATUS`).
- Status transitions enforce lifecycle rules:
  - only `pending` can be marked sent/canceled.
- Soft-deleted reminders (`deleted_at` set) are excluded from all repository query methods.

## Background Job Integration

`app/core/background_jobs.py` includes `daily_reminder_job`, which:
- fetches pending reminders due now (`send_on <= today`)
- sends notifications via `NotificationService.notify_payment_reminder`
- marks reminders as sent only after successful notification

## Cross-Domain Integration

- `businesses`: every reminder is business-scoped and validates `business_id`.
- `tax_deadline`: creating a tax deadline auto-creates a `tax_deadline_approaching` reminder (`days_before=7`).
- `charge`: issuing a charge auto-creates an `unpaid_charge` reminder (`days_unpaid=30`).

## Error Envelope

Domain errors use stable codes such as:
- `REMINDER.NOT_FOUND`
- `REMINDER.INVALID_STATUS`
- `REMINDER.NEGATIVE_DAYS`
- `REMINDER.MESSAGE_REQUIRED`

## Tests

Reminders test suites:
- `tests/reminders/api/test_reminders.py`
- `tests/reminders/api/test_reminders_create_mark_sent_additional.py`
- `tests/reminders/service/test_reminders.py`
- `tests/reminders/service/test_factory_additional.py`
- `tests/reminders/service/test_factory_extended_additional.py`
- `tests/reminders/repository/test_reminder_repository.py`

Run only this domain:

```bash
pytest tests/reminders -q
```
