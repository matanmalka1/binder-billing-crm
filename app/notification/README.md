# Notification Module

> Last audited: 2026-05-27 (notification schema v2 / Phase 2).

Manages notification audit records, manual preview/send, and the limited automatic binder handover send path.

## Scope

This module provides:
- Notification persistence in `notifications`
- Notification list and summary endpoints
- Advisor-only manual preview and send flow
- Email-only delivery for current Phase 1/2 implementation
- Policy checks before delivery
- `business_name`, `client_name`, trigger label, and domain label enrichment for list responses

## Domain Model

`Notification` fields:
- `id` (PK)
- `client_record_id` (FK -> `client_records.id`, required primary anchor)
- `business_id` (FK -> `businesses.id`, optional context)
- `binder_id` (FK -> `binders.id`, optional)
- `annual_report_id` (FK -> `annual_reports.id`, optional)
- `signature_request_id` (FK -> `signature_requests.id`, optional)
- `entity_type`, `entity_id` (generic domain anchor)
- `trigger` (enum, required)
- `channel` (enum, required)
- `recipient` (nullable; skipped records use `null`)
- `content_snapshot`, `subject_snapshot`
- `status` (`pending`, `sent`, `failed`, `skipped`)
- `sent_at`, `failed_at`, `error_message`, `retry_count`
- `idempotency_key`, `request_hash`
- `triggered_by` (FK -> `users.id`, nullable; `null` means system-triggered)
- `created_at`

Trigger enum values:
- `binder_ready_for_handover`
- `binder_missing_documents`
- `binder_general_reminder`
- `invoice_issued`
- `payment_reminder`
- `vat_documents_reminder`
- `annual_report_documents_request`
- `annual_report_client_reminder`
- `signature_request_sent`
- `signature_request_reminder`
- `client_missing_information`
- `client_documents_request`
- `client_general_message`

Implementation references:
- Model: `app/notification/models/notification.py`
- Repository: `app/notification/repositories/notification_repository.py`
- Facade: `app/notification/services/notification_service.py`
- Manual path: `app/notification/services/notification_send_service.py`
- Automatic path: `app/notification/services/notification_auto_send_service.py`
- Policy checks: `app/notification/services/notification_policy_service.py`
- Context resolution: `app/notification/services/notification_context_resolver.py`
- Template rendering: `app/notification/services/notification_template_renderer.py`
- Email delivery: `app/notification/services/notification_delivery_service.py`
- API: `app/notification/api/notifications.py`

## Service Architecture

| Class | File | Responsibility |
|---|---|---|
| `NotificationService` | `notification_service.py` | Public facade for preview, send, list, and summary |
| `NotificationSendService` | `notification_send_service.py` | Manual preview/send, validation, policy, contact resolution, record creation |
| `NotificationAutoSendService` | `notification_auto_send_service.py` | Internal auto-send path; only `binder_ready_for_handover` is allowed |
| `NotificationPolicyService` | `notification_policy_service.py` | Trigger-specific allow/block rules |
| `NotificationDeliveryService` | `notification_delivery_service.py` | Sends already-resolved email content; does not persist records |

## API

Router prefix is `/api/v1/notifications` (mounted through `app/router_registry.py`).

### List notifications
- `GET /api/v1/notifications`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_record_id` (optional)
  - `business_id` (optional)
  - `status` (optional; `pending` | `sent` | `failed` | `skipped`)
  - `trigger` (optional)
  - `channel` (optional)
  - `triggered_by` (optional)
  - `date_from`, `date_to` (optional)
  - `page` (default `1`)
  - `page_size` (allowed values: `25`, `50`)

### Summary
- `GET /api/v1/notifications/summary`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_record_id` (optional)
  - `business_id` (optional)
- Response includes `pending`, `sent`, `failed`, `skipped`, and `total`.

### Preview manual notification
- `POST /api/v1/notifications/preview`
- Role: `ADVISOR`
- Body:

```json
{
  "client_record_id": 1,
  "trigger": "client_general_message",
  "entity_id": null,
  "business_id": null,
  "confirm_recent_duplicate": false
}
```

### Send manual notification
- `POST /api/v1/notifications/send`
- Role: `ADVISOR`
- Body:

```json
{
  "client_record_id": 1,
  "trigger": "client_general_message",
  "subject": "נושא ההודעה",
  "body": "גוף ההודעה",
  "entity_id": null,
  "business_id": null,
  "idempotency_key": "optional-key",
  "confirm_recent_duplicate": false
}
```

## Behavior Notes

- Manual send validates trimmed subject/body before policy, contact resolution, delivery, or DB writes.
- Blocked policy returns `status="blocked"` and creates no notification record.
- Missing client email creates a `skipped` notification with `recipient=null`.
- Successful email delivery marks the record `sent`; failed email delivery marks it `failed`.
- `NotificationDeliveryService` does not create or update notification records.
- Annual report manual triggers require `entity_id` and save it as `annual_report_id`.
- `annual_report_client_reminder` requires `PENDING_CLIENT` and has a 2-day cooldown based on the last `sent` notification.
- `annual_report_documents_request` requires one of the allowed annual-report statuses.
- Annual report ownership is checked against `client_record_id`.
- Timeline includes only sent and failed notification events.

## Automatic Sends

- `NotificationAutoSendService` is an internal service, not an HTTP API.
- The only allowed automatic trigger is `binder_ready_for_handover`.
- `BinderLifecycleService.mark_ready_for_handover()` returns `(binder, notification)`.
- Binder ready-for-handover API responses include both the binder and notification result.

## Tests

```bash
JWT_SECRET=test-secret pytest -q tests/notification
```
