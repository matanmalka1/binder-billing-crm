# Reminders Module

Manages proactive reminder scheduling and lifecycle (pending/sent/canceled) for client-related events such as tax deadlines, idle binders, unpaid charges, and custom reminders.

## Scope

This module provides:
- Reminder creation for multiple reminder types
- Pending reminders listing by send date
- Client-scoped and status-scoped reminder listing
- Reminder retrieval by id
- Reminder status transitions (`pending -> sent` / `pending -> canceled`)
- Role-based API access

## Domain Model

`Reminder` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `reminder_type` (enum, required)
- `status` (enum, default `pending`)
- `target_date` (required)
- `days_before` (required)
- `send_on` (calculated send date)
- Optional references:
  - `binder_id` (FK -> `binders.id`)
  - `charge_id` (FK -> `charges.id`)
  - `tax_deadline_id` (FK -> `tax_deadlines.id`)
  - `annual_report_id` (FK -> `annual_reports.id`)
- `message` (required)
- `created_at`, `sent_at`, `canceled_at`
- `created_by` (FK -> `users.id`, optional)

Reminder type enum values:
- `tax_deadline_approaching`
- `binder_idle`
- `unpaid_charge`
- `custom`

Reminder status enum values:
- `pending`
- `sent`
- `canceled`

Implementation references:
- Model: `app/reminders/models/reminder.py`
- Schemas: `app/reminders/schemas/reminders.py`
- Repository: `app/reminders/repositories/reminder_repository.py`
- Services: `app/reminders/services/reminder_service.py`, `app/reminders/services/factory.py`, `app/reminders/services/reminder_queries.py`, `app/reminders/services/status_changes.py`
- API routers: `app/reminders/api/routers.py` + route modules in `app/reminders/api/`

## API

Router prefix is `/api/v1/reminders` (mounted in `app/main.py`).

Roles: `ADVISOR`, `SECRETARY` for all reminders endpoints.

### Create reminder
- `POST /api/v1/reminders/`
- Body (`ReminderCreateRequest`):

```json
{
  "client_id": 123,
  "reminder_type": "custom",
  "target_date": "2026-03-20",
  "days_before": 3,
  "message": "Reminder text"
}
```

Type-specific required fields:
- `tax_deadline_approaching` -> requires `tax_deadline_id`
- `binder_idle` -> requires `binder_id`
- `unpaid_charge` -> requires `charge_id`
- `custom` -> requires non-empty `message`

### List reminders
- `GET /api/v1/reminders/`
- Query params:
  - `status` (optional: `pending|sent|canceled`)
  - `client_id` (optional)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

Behavior:
- If `client_id` is provided, returns reminders for that client.
- Otherwise returns by status; default is pending reminders due on/before today.

### Get reminder
- `GET /api/v1/reminders/{reminder_id}`
- Returns single reminder.

### Cancel reminder
- `POST /api/v1/reminders/{reminder_id}/cancel`
- Valid only from `pending`.

### Mark reminder as sent
- `POST /api/v1/reminders/{reminder_id}/mark-sent`
- Valid only from `pending`.

## Behavior Notes

- Creation validates referenced entities:
  - Client must exist.
  - Tax deadline / binder / charge must exist for matching reminder types.
- Date behavior:
  - For deadline/custom reminders: `send_on = target_date - days_before`.
  - For binder idle / unpaid charge reminders: `send_on = today`.
- Negative day values are rejected (`REMINDER.NEGATIVE_DAYS`).
- Invalid status filter in list is rejected (`REMINDER.INVALID_STATUS`).
- Status transitions enforce lifecycle rules:
  - Only `pending` can be marked sent/canceled.
- List responses are enriched with `client_name` via batched client lookup.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `REMINDER.NOT_FOUND`
- `REMINDER.INVALID_STATUS`
- `REMINDER.NEGATIVE_DAYS`
- `REMINDER.MESSAGE_REQUIRED`

## Cross-Domain Integration

- `clients` integration:
  - Every reminder is client-scoped and validates client existence.
- `tax_deadline` integration:
  - Tax-deadline reminders validate referenced `tax_deadline_id`.
- `binders` integration:
  - Idle-binder reminders validate `binder_id`.
- `charge` integration:
  - Unpaid-charge reminders validate `charge_id`.
- `billing` integration:
  - `BillingService.issue_charge` creates unpaid-charge reminders through `ReminderService`.

## Tests

Reminders test suites:
- `tests/reminders/api/test_reminders.py`
- `tests/reminders/service/test_reminders.py`
- `tests/reminders/repository/test_reminder_repository.py`

Run only this domain:

```bash
pytest tests/reminders -q
```
