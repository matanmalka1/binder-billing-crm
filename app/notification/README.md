# Notification Module

> Last audited: 2026-05-16 (delivery-log refactor).

Manages notification records and delivery orchestration (email/WhatsApp) for binder lifecycle updates and manual reminders.

## Scope

This module provides:
- Notification persistence in `notifications`
- Delivery-status summary endpoint (bell badge source)
- Advisor-only manual send endpoint
- Channel orchestration (WhatsApp first when requested/configured, email fallback)
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
- `binder_ready_for_handover`
- `handover_reminder`
- `annual_report_client_reminder`
- `manual_payment_reminder`

Severity enum values:
- `info`
- `warning`
- `urgent`
- `critical`

Implementation references:
- Model: `app/notification/models/notification.py`
- Repository: `app/notification/repositories/notification_repository.py`
- Template renderer: `app/notification/services/notification_template_renderer.py`
- Delivery service: `app/notification/services/notification_delivery_service.py`
- Service (facade): `app/notification/services/notification_service.py`
- API: `app/notification/api/notifications.py`

## Service Architecture

The service layer is split into three classes:

| Class | File | Responsibility |
|---|---|---|
| `NotificationService` | `notification_service.py` | Public facade — validation, orchestration, list, summary |
| `NotificationTemplateRenderer` | `notification_template_renderer.py` | Template lookup + format; raises `AppError` on failure |
| `NotificationDeliveryService` | `notification_delivery_service.py` | Channel selection, WhatsApp→email fallback, persistence |

All domain callers (`BinderPickupReminderService`, `AnnualReportClientReminderService`, etc.) import and instantiate `NotificationService` only.

## API

Router prefix is `/api/v1/notifications` (mounted through `app/router_registry.py`).

### List notifications
- `GET /api/v1/notifications`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_record_id` (optional)
  - `business_id` (optional)
  - `status` (optional; `pending` | `sent` | `failed`)
  - `trigger` (optional)
  - `channel` (optional; `email` | `whatsapp`)
  - `page` (default `1`)
  - `page_size` (default `20`, min `1`, max `100`)
- Response items include `business_name` (enriched from `BusinessRepository`).

### Delivery status summary
- `GET /api/v1/notifications/summary`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_record_id` (optional)
  - `business_id` (optional)
- Response: `{ pending, sent, failed, total }` — absent statuses always `0`.
- Frontend bell badge sources from `pending + failed`.

### Send manual notification
- `POST /api/v1/notifications/send`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_record_id": 1,
  "business_id": 123,
  "preferred_channel": "email",
  "message": "Reminder message"
}
```

Notes:
- `preferred_channel` defaults to `email`.
- Manual sends use trigger `manual_payment_reminder` internally.
- Client ownership of the business is validated before sending.

## Behavior Notes

- `NotificationTemplateRenderer.render()` raises `AppError` (code `NOTIFICATION.TEMPLATE_ERROR`) if template is missing or a key is absent — no partial state is persisted.
- If WhatsApp fails, the failure record is persisted (`status=failed`) and the service falls through to email.
- Delivery outcome is tracked for **both** channels:
  - Initial record: `pending`
  - On success: `sent` + `sent_at`
  - On failure: `failed` + `failed_at` + `error_message`
- `business_name` enrichment in list responses is attached only when `business_id` is present.

## Error Codes

- `NOTIFICATION.TEMPLATE_ERROR` — template missing or required key absent in `template_data`.
- `NOTIFICATION.BUSINESS_NOT_FOUND` — `business_id` does not exist.
- `NOTIFICATION.BUSINESS_MISMATCH` — business belongs to a different client.
- `CLIENT.NOT_FOUND` — `client_record_id` does not exist.

## Cross-Domain Integration

- `binders` integration:
  - `BinderPickupReminderService` → `notify_client(trigger=BINDER_READY_FOR_PICKUP)`.
- `annual_reports` integration:
  - `AnnualReportClientReminderService` → `notify_client(trigger=...)`.
- `businesses` + `clients` integration:
  - Business ownership validated before delivery when `business_id` is provided.
  - `business_name` enriched in `NotificationService` via `BusinessRepository.list_by_ids`.
- `infrastructure` integration:
  - Uses `EmailChannel` and `WhatsAppChannel` from `app/infrastructure/notifications.py`.

## Tests

```bash
JWT_SECRET=test-secret pytest -q tests/notification
```
