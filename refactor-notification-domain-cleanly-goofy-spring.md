# Notification Domain Refactor — Delivery Log Model

## Context

Notifications are outbound delivery records, not an inbox. The current model carries `is_read` / `read_at` columns and a `count_unread` / `unread-count` endpoint that encode the wrong mental model. This refactor strips all read-state, splits the monolithic `NotificationService` into focused classes, adds proper filters to the list endpoint, and replaces `unread-count` with a delivery-status summary endpoint. No backward compatibility required. Frontend updated in scope.

---

## Critical Files

| File | Action |
|------|--------|
| `app/notification/models/notification.py` | Drop `is_read`, `read_at` columns and docstring references |
| `app/notification/repositories/notification_repository.py` | Drop `count_unread`, `list_recent`; extend `list_paginated` with new filters; add `count_by_status` |
| `app/notification/services/notification_template_renderer.py` | **New** — template lookup + subject; raises AppError on any failure |
| `app/notification/services/notification_delivery_service.py` | **New** — WhatsApp/email delivery, persistence; injected repo |
| `app/notification/services/notification_service.py` | Drop `count_unread`, `_deliver_*`; add `get_summary`, `send_manual`; delegate to new classes |
| `app/notification/api/notifications.py` | Replace `unread-count` with `summary`; add filters to list; call `svc.send_manual` |
| `app/notification/schemas/notification_schemas.py` | Drop `UnreadCountResponse`; add `NotificationSummaryResponse`; default `preferred_channel` to email |
| `app/notification/README.md` | Update to reflect new 3-class architecture |
| `alembic/versions/0008_drop_notification_read_state.py` | **New** — drop `is_read`, `read_at` |
| `alembic/README` | Update current head to `0008_drop_notification_read_state` |
| `tests/notification/api/test_notifications.py` | Replace; add summary + filter tests; keep auth coverage |
| `tests/notification/service/test_notification.py` | Update missing-template assertion to AppError; add summary + mismatch tests |
| `tests/notification/service/test_notification_reminders.py` | Update missing-template tests to expect AppError |
| `tests/notification/service/test_notification_send_service.py` | Delete — coverage absorbed into updated service tests |
| `tests/notification/repository/test_notification_repository.py` | Drop `count_unread`; add filter + `count_by_status` tests |
| `src/features/notifications/api/contracts.ts` | Replace `UnreadCountResponse` with `NotificationSummaryResponse`; add filter fields |
| `src/features/notifications/api/endpoints.ts` | Replace `notificationsUnreadCount` with `notificationsSummary` |
| `src/features/notifications/api/notifications.api.ts` | Replace `getUnreadCount` with `getSummary` |
| `src/features/notifications/api/queryKeys.ts` | Rename `unreadCount` → `summary` |
| `src/features/notifications/hooks/useNotificationBell.ts` | Source badge count from `pending + failed` |

---

## Step-by-Step Plan

### 1. Alembic Migration `0008_drop_notification_read_state`

File: `alembic/versions/0008_drop_notification_read_state.py`

- `revision = "0008_drop_notification_read_state"`
- `down_revision = "0007_remove_signature_request_draft"`
- `upgrade()`:
  ```python
  op.drop_column("notifications", "is_read")
  op.drop_column("notifications", "read_at")
  ```
- `downgrade()`: restore both columns safely for non-null:
  ```python
  op.add_column("notifications", sa.Column("read_at", sa.DateTime(), nullable=True))
  op.add_column("notifications", sa.Column(
      "is_read", sa.Boolean(), nullable=False,
      server_default=sa.text("false"),
  ))
  op.alter_column("notifications", "is_read", server_default=None)
  ```
- Follow docstring format from `0007_remove_signature_request_draft.py`

Update `alembic/README`: change stale "Current head is `0006_simplify_annual_report_statuses`" to `0008_drop_notification_read_state`.

---

### 2. ORM Model — `app/notification/models/notification.py`

Remove:
- `is_read` column
- `read_at` column
- Docstring line: `- is_read / read_at support the notification center UI (bell icon).`
- Import `Boolean` from sqlalchemy (no longer needed if only used for `is_read`)

No enum changes. Existing 3 composite indexes are fine.

---

### 3. New: `NotificationTemplateRenderer`

File: `app/notification/services/notification_template_renderer.py`

```python
class NotificationTemplateRenderer:
    def render(
        self,
        trigger: NotificationTrigger,
        template_data: dict,
        person_name: str,
    ) -> tuple[str, str]:
        """Returns (content, subject). Raises AppError before any persistence."""
```

- Look up template in `CONTENT_TEMPLATES` — if missing, raise `AppError`
- Format with `{name}` + `template_data` — if `KeyError`, raise `AppError`
- Look up subject from a `SUBJECTS` mapping — fall back to `DEFAULT_NOTIFICATION_SUBJECT`
- Return `(content, subject)`
- Hebrew error: `"תבנית ההודעה חסרה או שדה חסר בנתוני ההודעה"`, code `"NOTIFICATION.TEMPLATE_ERROR"`
- Never returns `None`; callers always get a tuple or an exception

`app/notification/services/messages.py` — add a public `SUBJECTS` mapping (rename/expose the private `_SUBJECTS` currently in `notification_service.py`):
```python
SUBJECTS: dict[NotificationTrigger, str] = {
    NotificationTrigger.BINDER_RECEIVED: BINDER_RECEIVED_SUBJECT,
    ...
}
```
Remove `_SUBJECTS` from `notification_service.py` and import `SUBJECTS` from `messages.py` in the renderer. Do not import from a private name.

---

### 4. New: `NotificationDeliveryService`

File: `app/notification/services/notification_delivery_service.py`

```python
class NotificationDeliveryService:
    def __init__(
        self,
        repo: NotificationRepository,
        email: EmailChannel,
        whatsapp: WhatsAppChannel,
    ):
        self.repo = repo  # injected — shared with NotificationService
        self.email = email
        self.whatsapp = whatsapp

    def deliver(
        self,
        person: Person,
        client_record_id: int,
        trigger: NotificationTrigger,
        content: str,
        subject: str,
        preferred_channel: NotificationChannel,
        severity: NotificationSeverity,
        business_id: Optional[int],
        binder_id: Optional[int],
        annual_report_id: Optional[int],
        triggered_by: Optional[int],
        log_ctx: str,
    ) -> bool:
        """WhatsApp → email fallback. Persists attempt records."""
```

- Extract `_deliver_to_contact` and `_deliver` from `NotificationService` verbatim
- Rename public method to `deliver`, private channel method to `_send_to_channel`
- `NotificationService` creates a single `NotificationRepository` and passes it to both `NotificationDeliveryService` and itself

---

### 5. Refactored `NotificationService`

File: `app/notification/services/notification_service.py`

Public API:
- `notify_client(client_record_id, trigger, template_data, business_id?, ...)` — generic entry point used by reminders and internal flows
  - If `client_record_id` does not exist: raise `NotFoundError("הלקוח לא נמצא", "CLIENT.NOT_FOUND")` — applies in both `notify_client` and `send_manual`. Do not silently return `False` for a missing client.
- If `business_id` provided:
  1. Fetch business by id — if not found, raise `AppError("העסק לא נמצא", "NOTIFICATION.BUSINESS_NOT_FOUND")`
  2. Fetch `ClientRecord` by `client_record_id` to get its `legal_entity_id`
  3. If `business.legal_entity_id != client_record.legal_entity_id`, raise `AppError("העסק אינו שייך ללקוח שצוין", "NOTIFICATION.BUSINESS_MISMATCH")`
  - Validation uses `ClientRecord.legal_entity_id` + `Business.legal_entity_id` — does NOT depend on the resolved `Person` contact (a client with no owner/email can still fail business ownership validation)

Note: `notify_client` raising on missing `client_record_id` is a behavior change for internal reminder flows — but reminder services always pass a valid `client_record_id` from their own prior fetch, so this should be safe.
  - Delegates rendering to `NotificationTemplateRenderer.render()` (raises AppError on failure — propagates up)
  - Delegates delivery to `NotificationDeliveryService.deliver()`
- **New** `send_manual(request: ManualSendRequest, triggered_by: int) -> bool` — entry point for API manual sends
  - Validates `client_record_id` exists (raises `NotFoundError` with Hebrew message if not)
  - Validates `business_id` if provided (same ownership check as `notify_client`)
  - Calls `notify_client(...)` with `trigger=MANUAL_PAYMENT_REMINDER`
- `list_paginated(page, page_size, client_record_id?, business_id?, status?, trigger?, channel?)` — pass new filters through to repo
- **New** `get_summary(client_record_id?, business_id?) -> NotificationSummaryResponse` — calls `repo.count_by_status(...)`, returns all four keys with zero for absent statuses

Drop:
- `count_unread()`
- `_deliver_to_contact()`
- `_deliver()`

---

### 6. Repository — `app/notification/repositories/notification_repository.py`

Remove:
- `count_unread()` — verify no callers remain first (`rg "count_unread" app/ tests/`)
- `list_recent()` — verify `NotificationRepository.list_recent` has no callers (`rg "list_recent" app/ tests/`; dashboard uses its own repos)

Extend `list_paginated`:
```python
def list_paginated(
    self,
    page: int = 1,
    page_size: int = 20,
    client_record_id: Optional[int] = None,
    business_id: Optional[int] = None,
    status: Optional[NotificationStatus] = None,
    trigger: Optional[NotificationTrigger] = None,
    channel: Optional[NotificationChannel] = None,
) -> tuple[list[Notification], int]:
```

Add:
```python
def count_by_status(
    self,
    client_record_id: Optional[int] = None,
    business_id: Optional[int] = None,
) -> dict[str, int]:
    """Returns {pending, sent, failed, total} — absent statuses always 0."""
```

Use `func.count` + `group_by(Notification.status)`, aggregate to dict, then:
```python
result = {s.value: 0 for s in NotificationStatus}
result["total"] = 0
for status_val, count in rows:
    key = status_val.value if isinstance(status_val, NotificationStatus) else status_val
    result[key] = count
    result["total"] += count
return result
```

Note: SQLAlchemy may return enum objects rather than string values depending on dialect; normalize with `.value` before using as dict key.

---

### 7. Schemas — `app/notification/schemas/notification_schemas.py`

Remove:
- `UnreadCountResponse`

Add:
```python
class NotificationSummaryResponse(BaseModel):
    pending: int
    sent: int
    failed: int
    total: int
```

Update `ManualSendRequest`:
- `preferred_channel: NotificationChannel = NotificationChannel.EMAIL`  (was required, now defaults to email)

`NotificationResponse` — no changes (never had `is_read`/`read_at`).

---

### 8. API Router — `app/notification/api/notifications.py`

Replace `unread-count` endpoint with:
```python
@router.get("/summary", response_model=NotificationSummaryResponse)
def get_notification_summary(
    db: DBSession,
    user: CurrentUser,
    client_record_id: Optional[int] = None,
    business_id: Optional[int] = None,
):
    svc = NotificationService(db)
    return svc.get_summary(client_record_id=client_record_id, business_id=business_id)
```

Update list endpoint to pass new filters:
```python
status: Optional[NotificationStatus] = None,
trigger: Optional[NotificationTrigger] = None,
channel: Optional[NotificationChannel] = None,
```

Update manual send endpoint — router calls `svc.send_manual(body, user.id)`:
```python
@advisor_router.post("/send", response_model=ManualSendResponse)
def send_manual_notification(body: ManualSendRequest, db: DBSession, user: CurrentUser):
    svc = NotificationService(db)
    ok = svc.send_manual(body, triggered_by=user.id)
    return ManualSendResponse(ok=ok)
```

Router does no validation — all logic in service.

---

### 9. Tests

**Delete:** `tests/notification/service/test_notification_send_service.py` — duplicate coverage absorbed below.

**`tests/notification/api/test_notifications.py`** — rewrite (preserve advisor/secretary auth coverage):
- `test_notifications_list` — list by `business_id`
- `test_notifications_list_by_status` — filter by status
- `test_notifications_list_by_trigger` — filter by trigger
- `test_notifications_list_by_channel` — filter by channel
- `test_notifications_summary` — checks `pending/sent/failed/total`; zero for absent statuses
- `test_unread_count_route_gone` — assert `/api/v1/notifications/unread-count` returns 404
- `test_secretary_can_list` — secretary role allowed
- `test_secretary_cannot_send` — secretary POST /send returns 403

**`tests/notification/service/test_notification.py`** — update:
- `test_notify_client_missing_template_key_raises_app_error` — update from `ok is False` to `pytest.raises(AppError)`
- Add `test_notify_client_rejects_mismatched_business_id` — different client's business → AppError
- Add `test_get_summary_returns_correct_counts` — seed SENT + FAILED, check all four keys
- Add `test_get_summary_returns_zeros_for_absent_statuses` — no PENDING → `pending == 0`
- Keep: `test_notify_client_sends_by_client_record_id`, `test_notify_client_business_id_is_optional_context`, `test_notify_client_whatsapp_fails_falls_back_to_email`
- Add `test_notify_client_email_failure_persists_failed_record` — email returns `(False, "err")` → FAILED record persisted

**`tests/notification/service/test_notification_reminders.py`** — update:
- Any test asserting `ok is False` on missing template → update to `pytest.raises(AppError)`
- Keep cooldown and status-check tests unchanged

**`tests/notification/repository/test_notification_repository.py`** — update:
- Remove any `count_unread` calls
- Add `test_list_paginated_filters_by_status`
- Add `test_list_paginated_filters_by_trigger`
- Add `test_list_paginated_filters_by_channel`
- Add `test_count_by_status_returns_correct_counts`
- Add `test_count_by_status_returns_zero_for_absent_statuses`

**`tests/notification/repository/test_notification_trigger_queries.py`** — no changes.

**`tests/binders/service/test_binder_pickup_reminder_service.py`** — no changes.

**`tests/annual_reports/service/test_client_reminder_service.py`** — no changes.

---

### 10. Cleanup

- `app/notification/README.md` — update (do not delete): reflect 3-class architecture (`NotificationTemplateRenderer`, `NotificationDeliveryService`, `NotificationService`), remove stale `NotificationSendService` reference
- `list_recent` removal: run `rg "\.list_recent(" app/ tests/` to find all callers across the codebase; confirm none are on a `NotificationRepository` instance before removing

Dead-reference grep after implementation (scoped to notification domain):
```bash
git grep "count_unread\|unread_count\|unread-count\|is_read\|read_at\|read_by\|UnreadCountResponse\|NotificationSendService" \
  -- app/notification/ tests/notification/
```

---

## Architecture Summary After Refactor

```
NotificationService                ← public interface, validation, orchestration
  ├─ notify_client(...)            ← generic entry; reminder services call this
  ├─ send_manual(request, ...)     ← manual send with client/business validation
  ├─ list_paginated(...)           ← delivery log with 5 filters
  └─ get_summary(...)              ← {pending, sent, failed, total}
  
  delegates to:
  ├─ NotificationTemplateRenderer  ← render() -> (content, subject) or AppError
  ├─ NotificationDeliveryService   ← deliver() with injected repo, WhatsApp→email fallback
  └─ NotificationRepository        ← ORM queries only

BinderPickupReminderService        ← owns cooldown + READY_FOR_PICKUP check → notify_client()
AnnualReportClientReminderService  ← owns cooldown + PENDING_CLIENT check → notify_client()
```

---

## Frontend Changes

Files under `src/features/notifications/`:

### `api/contracts.ts`
- Remove `UnreadCountResponse`
- Add:
  ```typescript
  export interface NotificationSummaryResponse {
    pending: number
    sent: number
    failed: number
    total: number
  }
  ```
- Add to `ListNotificationsParams`:
  ```typescript
  status?: string
  trigger?: string
  channel?: string
  ```

### `api/endpoints.ts`
- Replace `notificationsUnreadCount: '/notifications/unread-count'` with `notificationsSummary: '/notifications/summary'`

### `api/notifications.api.ts`
- Remove `getUnreadCount()`; remove `UnreadCountResponse` import
- Add:
  ```typescript
  getSummary: async (clientId?: number): Promise<NotificationSummaryResponse> => {
    const response = await api.get<NotificationSummaryResponse>(
      NOTIFICATION_ENDPOINTS.notificationsSummary,
      clientId != null ? { params: toQueryParams({ client_record_id: clientId }) } : undefined,
    )
    return response.data
  },
  ```

### `api/queryKeys.ts`
- Rename `unreadCount` → `summary`:
  ```typescript
  summary: (clientId?: number) => ['notifications', 'summary', clientId ?? 'global'] as const,
  ```

### `hooks/useNotificationBell.ts`
- Call `getSummary` instead of `getUnreadCount`; use `notificationsQK.summary()` key
- Rename returned value from `unreadCount` to `badgeCount`
- Source from: `(data?.pending ?? 0) + (data?.failed ?? 0)` — highlights attention-needed deliveries; never use `total` (grows unbounded)

### `components/layout/NotificationBell.tsx`
- Update destructure: `const { drawerOpen, badgeCount, handleOpen, handleClose } = useNotificationBell()`
- Replace all `unreadCount` references with `badgeCount` (3 occurrences: conditional, aria-label, display)

### `api/index.ts`
- Update exports to remove `UnreadCountResponse`, add `NotificationSummaryResponse`

---

## Verification

```bash
# Backend tests
JWT_SECRET=test-secret pytest -q \
  tests/notification \
  tests/binders/service/test_binder_pickup_reminder_service.py \
  tests/annual_reports/service/test_client_reminder_service.py

# Dead refs — notification domain only (exclude alembic; 0001 and 0008 downgrade legitimately reference these)
git grep "count_unread\|unread_count\|unread-count\|is_read\|read_at\|read_by\|UnreadCountResponse\|NotificationSendService" \
  -- app/notification/ tests/notification/

# Confirm list_recent callers before removal
rg "\.list_recent(" app/ tests/

# Frontend type check
cd ../frontend && npm run typecheck
```

Migration:
- `down_revision = "0007_remove_signature_request_draft"`
- `downgrade()` adds `is_read` with `server_default=sa.text("false")` then removes server_default (non-null backfill pattern)
- `get_summary` / `count_by_status` must return explicit zeros for absent statuses — never omit keys
