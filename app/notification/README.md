# Notification Module

> Last audited: 2026-05-27 (notification schema v2 / Phase 2).

Manages notification audit records, manual preview/send, and the limited automatic binder handover send path.

## Product Overview

The Notifications module is the system’s control center for every message sent to a client or recorded as a delivery attempt.

Its goal is to let the office team communicate with clients in an organized, consistent, and controlled way around operational events: document requests, reminders, VAT filings, annual reports, charges, invoices, signature requests, and binder handovers.

At the product level, notifications solve three main problems:

Controlled sending: before a message is sent, the system checks whether it is allowed based on the client status, trigger type, and related entity.

Full audit trail: every meaningful send attempt is recorded with status, recipient, message content, trigger type, and the user who initiated the action.

Team visibility: users can view the notifications list, filter by client, business, status, message type, or date, and see a summary of sent, failed, skipped, or pending messages.

### What the product does

The module allows an advisor to send manual messages to clients from a clear business context.

For example, an advisor can send a document request for an annual report, a reminder to a client waiting for approval, a payment reminder, a general message, or a request to complete missing details.

Before sending, the advisor can preview the message to see the recipient, subject, and body exactly as they are expected to be sent.

The system does not treat a notification as free text only.

Each notification is connected to a client, and sometimes also to a business, binder, annual report, charge, signature request, or another entity in the system.

This link is important so the team can later understand why the message was sent, which process created it, and what the result was.

The module also supports limited automatic sending.

At this stage, the main automatic send is the notification that a binder is ready for handover.

This send is triggered from the binder flow itself, not from the manual sending screen.

### Permissions and user roles

The module is intended for two user types:

`ADVISOR`: can view notifications, see summaries, preview messages, and send manual messages.

`SECRETARY`: can view notifications and summaries, but is not responsible for sending manual messages.

This split reflects the office’s responsibility model:

The advisor makes the professional decision about whether it is appropriate to send a message to the client, while secretarial and operations staff can track communication status and sending history.

### Notification lifecycle

The notification lifecycle starts from a business trigger.

A trigger is the reason a message should be sent, for example:

A binder is ready for handover.

Documents are missing for a binder.

Documents are required for an annual report.

An annual report is waiting for the client.

A VAT reminder is approaching.

An invoice was issued.

A payment reminder is required.

A signature request was sent or requires a reminder.

Client details or client documents are missing.

After the trigger is selected, the system runs policy checks.

These checks verify that the message is relevant and allowed.

For example, the system does not send regular messages to a closed or frozen client, does not send an annual report reminder if the report is not in the correct status, and does not send a VAT reminder if the deadline has already passed or if the client is not required to file VAT.

If the policy blocks the send, no notification record is created.

If the policy allows sending but no valid recipient exists, the system creates a notification record with status `skipped`.

If a recipient exists, the system attempts to send the message and saves the result as `sent` or `failed`.

### Status meanings

Each notification has a status that explains what actually happened:

`pending`: a record was created before sending, or a previous attempt was interrupted.

`sent`: the message was sent successfully.

`failed`: a send attempt was made, but the external channel failed or returned an error.

`skipped`: the system did not send the message because no valid recipient was available, usually because of a missing email address.

A blocked status is not saved as a notification record.

When a message is blocked by business policy, the result is returned to the screen or API client, but it is not added to the notification history.

The reason is that a block is a policy decision made before a send attempt, not a communication event with the client.

### Delivery channels

At this stage, the active implementation is email delivery.

The module structure allows future expansion to additional channels, but right now the notification records, preview, and actual sending are designed around email.

In development and test environments, external delivery should not be sent to a real client.

In staging and production, delivery depends on the environment settings and the notifications enablement flag.

### Documentation and operational value

The module’s main value is not just sending messages, but creating a reliable operational history.

When a client claims they did not receive a document request, or when the team wants to know whether a reminder was already sent, they can check the notification records instead of relying on memory or manual email searches.

Each record stores a snapshot of the content that was sent at the time.

Even if message templates change in the future, the history still reflects what was actually sent at that moment.

The module also prevents duplicates in sensitive areas.

For example, some triggers check whether a reminder was sent recently, and some send flows use an idempotency key to prevent duplicate sending in cases of repeated clicks, page refreshes, or client retries.

### Product boundaries

The Notifications module is not a marketing system, not a mass mailing system, and not a replacement for an email inbox.

It is intended for focused operational communication around existing CRM workflows.

The module also does not decide every business process by itself.

It receives a trigger from another module or from a manual advisor action, checks whether sending is allowed, builds or receives the message content, sends it through the supported channel, and stores the result.

In other words: the module is a communication and audit layer for business events, not the source of truth for reports, binders, charges, or clients.
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
- Required header: `X-Idempotency-Key: <uuid>`
- Body:

```json
{
  "client_record_id": 1,
  "trigger": "client_general_message",
  "entity_id": null,
  "business_id": null,
  "channel": "email",
  "overrides": {
    "subject": "נושא ההודעה",
    "body": "גוף ההודעה"
  },
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
