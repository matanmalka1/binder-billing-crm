## [P2] 8.3 — סימון הכל כנקרא (Mark All as Read)
**Status:** MISSING
**Gap:** `Notification` model has no `is_read` field; no bulk mark-as-read endpoint or operation exists.
**Files to touch:**
- `app/notification/models/notification.py` — add `is_read: Boolean, default=False` and `read_at: DateTime, nullable`
- `app/notification/repositories/notification_repository.py` — add `mark_read(notification_ids)` and `mark_all_read(client_id)` methods
- `alembic/versions/` — migration for new columns
- A routed domain (e.g. `app/reminders/` or a new `app/notification_center/`) needs an HTTP endpoint: `POST /notifications/mark-read` (bulk) and `POST /notifications/mark-all-read`
**Acceptance criteria:** `POST /notifications/mark-all-read` sets `is_read=True` and `read_at=now()` on all unread notifications for the current advisor; returns count updated.

---

## [P2] 8.6 — פעמון התראות — Notification Center (Unread Count & List)
**Status:** MISSING
**Gap:** No endpoint exposes unread notification count or a notification inbox listing; the notification domain has no HTTP router.
**Files to touch:**
- `app/notification/repositories/notification_repository.py` — add `count_unread()` and `list_recent(limit)` queries (requires `is_read` field from 8.3)
- Create HTTP endpoints in an appropriate routed domain (e.g. `app/reminders/api/` or a new `notification_center` router) — `GET /notifications` and `GET /notifications/unread-count`
**Acceptance criteria:** `GET /notifications/unread-count` returns `{"unread_count": N}`; `GET /notifications?limit=20` returns paginated recent notifications with `is_read`, `created_at`, `trigger`, `content_snapshot`.

---

## [P2] 8.1 — מערכת 4 רמות התראה — Severity (Notification Severity)
**Status:** PARTIAL
**Gap:** 4 urgency levels exist for deadlines, but `Notification` model lacks a `severity` field to tag notifications by level (INFO/WARNING/URGENT/CRITICAL).
**Files to touch:**
- `app/notification/models/notification.py` — add `severity: Enum(NotificationSeverity)` with values INFO, WARNING, URGENT, CRITICAL; default INFO
- `app/notification/repositories/notification_repository.py` — include severity in queries
- `alembic/versions/` — migration
**Acceptance criteria:** All notification creation calls pass a severity level; notification list endpoint includes `severity` on each item.

---

## [P2] 8.4 — שליחת תזכורת — Bulk & WhatsApp (Bulk Send & WhatsApp)
**Status:** PARTIAL
**Gap:** Notifications send individually via email (SendGrid); no bulk send exists, and WhatsApp channel is a stub.
**Files to touch:**
- `app/notification/services/notification_service.py` — add `bulk_notify(client_ids, template, channel)` method
- `app/notification/services/notification_service.py` — implement WhatsApp channel (replace stub with actual API call when `WHATSAPP_API_KEY` is configured)
**Acceptance criteria:** `bulk_notify()` sends to a list of clients in a single call and records each notification; WhatsApp sends when the env var is present, falls back to email stub otherwise.

---

## [P3] 8.2 — כפתור פעולה לכל התראה — Tax Deadlines (Action Metadata for Deadlines)
**Status:** PARTIAL
**Gap:** `available_actions` metadata is computed for binders and clients but not for `TaxDeadline` or `AnnualReport` notifications.
**Files to touch:**
- `app/actions/action_contracts.py` — add action definitions for `TAX_DEADLINE` and `ANNUAL_REPORT` entity types
- `app/tax_deadline/services/tax_deadline_service.py` — attach `available_actions` to deadline response objects
- `app/annual_reports/services/query_service.py` — attach `available_actions` to report list/detail responses
**Acceptance criteria:** Tax deadline and annual report responses include `available_actions` array with applicable action slugs and labels.
