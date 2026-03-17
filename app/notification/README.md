# Notification Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages notification records and delivery orchestration (email/WhatsApp) for binder lifecycle updates and manual reminders.

## Scope

This module provides:
- Notification persistence in `notifications`
- Read/mark-read notification center endpoints
- Advisor-only manual send endpoint
- Channel orchestration (WhatsApp first when requested/configured, email fallback)
- Non-blocking send behavior (caller flow is not interrupted on delivery failures)

## Domain Model

`Notification` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `binder_id` (FK -> `binders.id`, optional)
- `trigger` (enum, required)
- `channel` (enum, required)
- `status` (enum, default `pending`)
- `severity` (enum, default `info`)
- `recipient` (required)
- `content_snapshot` (required)
- `sent_at`, `failed_at`, `error_message`
- `is_read` (default `false`), `read_at`
- `created_at`
- `triggered_by` (FK -> `users.id`, optional)

Channel enum values:
- `whatsapp`
- `email`

Status enum values:
- `pending`
- `sent`
- `failed`

Trigger enum values:
- `binder_received`
- `binder_ready_for_pickup`
- `manual_payment_reminder`

Severity enum values:
- `info`
- `warning`
- `urgent`
- `critical`

Implementation references:
- Model: `app/notification/models/notification.py`
- Repository: `app/notification/repositories/notification_repository.py`
- Service: `app/notification/services/notification_service.py`
- API: `app/notification/api/notifications.py`

## API

Router prefix is `/api/v1/notifications` (mounted in `app/main.py`).

### List recent notifications
- `GET /api/v1/notifications`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (optional)
  - `limit` (default `20`, min `1`, max `100`)

### Get unread count
- `GET /api/v1/notifications/unread-count`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (optional)

### Mark specific notifications as read
- `POST /api/v1/notifications/mark-read`
- Roles: `ADVISOR`, `SECRETARY`
- Body:

```json
{
  "notification_ids": [1, 2, 3]
}
```

### Mark all notifications as read
- `POST /api/v1/notifications/mark-all-read`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (optional)

### Send manual notification
- `POST /api/v1/notifications/send`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_id": 123,
  "channel": "WHATSAPP",
  "message": "Reminder message",
  "severity": "INFO"
}
```

Notes:
- `channel` accepted values are `WHATSAPP` / `EMAIL`.
- Manual sends use trigger `manual_payment_reminder` internally.

## Behavior Notes

- Service sends notifications via infrastructure channels:
  - `WhatsAppChannel` for WhatsApp when requested and configured.
  - `EmailChannel` as fallback/default.
- If WhatsApp fails, service falls back to email when client email exists.
- All send paths are non-blocking for callers: `send_notification` returns `True` even on transport failure.
- Delivery outcome is tracked in repository:
  - Initial record: `pending`
  - On success: `sent` + `sent_at`
  - On failure: `failed` + `failed_at` + `error_message`
- Read-state operations:
  - `mark_read(notification_ids)` updates unread target rows.
  - `mark_all_read(client_id?)` supports global or per-client bulk mark.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Role/access failures use the shared authorization handling.
Notification delivery failures are primarily recorded in persistence/logs rather than surfaced as blocking API failures.

## Cross-Domain Integration

- `binders` integration:
  - Binder receive/ready flows call `NotificationService` (`notify_binder_received`, `notify_ready_for_pickup`).
- `clients` integration:
  - Client contact data (phone/email) is used for channel routing/fallback.
- `infrastructure` integration:
  - Uses `EmailChannel` and `WhatsAppChannel` from `app/infrastructure/notifications.py`.
- `dashboard`/timeline integration:
  - Stored notifications are consumed by other read models (for example recent/unread and activity context).

## Tests

Notification test suites:
- `tests/notification/service/test_notification.py`
- `tests/notification/repository/test_notification_repository.py`

Related regression coverage:
- `tests/regression/test_core_regressions_binders_charges_notifications.py`

Run only this domain:

```bash
pytest tests/notification -q
```
