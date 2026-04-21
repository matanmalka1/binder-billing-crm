# Notification Module

> Last audited: 2026-03-22 (post-refactor sync).

Manages notification records and delivery orchestration (email/WhatsApp) for binder lifecycle updates and manual reminders.

## Scope

This module provides:
- Notification persistence in `notifications`
- Read/mark-read notification center endpoints
- Advisor-only manual send endpoint
- Channel orchestration (WhatsApp first when requested/configured, email fallback)
- Non-blocking send behavior (caller flow is not interrupted on delivery failures)
- `business_name` enrichment when notifications are scoped to a business

## Domain Model

`Notification` fields:
- `id` (PK)
- `client_record_id` (FK -> `client_records.id`, required primary anchor)
- `business_id` (FK -> `businesses.id`, optional context)
- `binder_id` (FK -> `binders.id`, optional)
- `trigger` (enum, required)
- `channel` (enum, required)
- `status` (enum, default `pending`)
- `severity` (enum, default `info`)
- `recipient` (required)
- `content_snapshot` (required)
- `sent_at`, `failed_at`, `error_message`
- `is_read` (default `false`), `read_at`
- `retry_count`
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
- Service (facade): `app/notification/services/notification_service.py`
- Service (delivery): `app/notification/services/notification_send_service.py`
- API: `app/notification/api/notifications.py`

## Service Architecture

The service layer is split into two classes:

| Class | File | Responsibility |
|---|---|---|
| `NotificationService` | `notification_service.py` | Public facade — used by API routers and cross-domain callers |
| `NotificationSendService` | `notification_send_service.py` | Low-level delivery: channel selection, persistence, WhatsApp/email send |

All domain callers (`BinderService`, `BillingService`, etc.) import and instantiate `NotificationService` only.

## API

Router prefix is `/api/v1/notifications` (mounted through `app/router_registry.py`).

### List recent notifications
- `GET /api/v1/notifications`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_record_id` (optional)
  - `business_id` (optional; narrows a client-scoped view)
  - `page` (default `1`)
  - `page_size` (default `20`, min `1`, max `100`)
- Response items include `business_name` (enriched from `BusinessRepository`).

### Get unread count
- `GET /api/v1/notifications/unread-count`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_record_id` (optional)
  - `business_id` (optional)

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
  - `client_record_id` (optional)
  - `business_id` (optional)

### Send manual notification
- `POST /api/v1/notifications/send`
- Role: `ADVISOR` only
- Body:

```json
{
  "business_id": 123,
  "channel": "whatsapp",
  "message": "Reminder message",
  "severity": "info"
}
```

Notes:
- `channel` accepted values are `whatsapp` / `email`.
- Manual sends use trigger `manual_payment_reminder` internally.

## Behavior Notes

- Service sends notifications via infrastructure channels:
  - `WhatsAppChannel` for WhatsApp when requested and configured.
  - `EmailChannel` as fallback/default.
- If WhatsApp fails, the failure is persisted (`status=failed`) and the service falls through to email.
- All send paths are non-blocking for callers: `send_notification` returns `True` even on transport failure.
- Delivery outcome is tracked in repository for **both** channels:
  - Initial record: `pending`
  - On success: `sent` + `sent_at`
  - On failure: `failed` + `failed_at` + `error_message`
- `bulk_notify` is capped at `_BULK_NOTIFY_LIMIT = 500` businesses per call. Exceeding this raises `NOTIFICATION.BULK_LIMIT_EXCEEDED`.
- `notify_binder_received` uses `binder.period_start` for the date in the message body.
- Read-state operations:
  - `mark_read(notification_ids)` updates unread target rows.
  - `mark_all_read(client_record_id?, business_id?)` supports global, per-client-record, or per-business bulk mark.
- `business_name` enrichment in list responses is attached only when `business_id` is present.
- If a trigger has no entry in `_SUBJECTS`, a warning is logged and a generic Hebrew subject is used.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors:
- `NOTIFICATION.BULK_LIMIT_EXCEEDED` — `bulk_notify` called with more than 500 business IDs.

Role/access failures use the shared authorization handling.
Notification delivery failures are recorded in persistence/logs rather than surfaced as blocking API failures.

## Cross-Domain Integration

- `binders` integration:
  - Binder receive/ready flows call `NotificationService.notify_binder_received` / `notify_ready_for_pickup`.
- `businesses` + `clients` integration:
  - Client-record and business contact data (phone/email) is used for channel routing/fallback inside `NotificationSendService`.
  - `business_name` is enriched in `NotificationService` via `BusinessRepository.list_by_ids`.
- `infrastructure` integration:
  - Uses `EmailChannel` and `WhatsAppChannel` from `app/infrastructure/notifications.py`.
- `dashboard`/timeline integration:
  - Stored notifications are consumed by other read models (recent/unread and activity context).

## Tests

Notification test suites:
- `tests/notification/service/test_notification.py`
- `tests/notification/repository/test_notification_repository.py`

Related regression coverage:
- `tests/regression/test_core_regressions_binders_charges_notifications.py`

Run only this domain:

```bash
JWT_SECRET=test-secret pytest -q tests/notification
```
