# TODO — Code Review Issues

> Issues 1–4 have been resolved. This file tracks the remaining open items.
> Severity: 🔴 Fix ASAP · 🟠 Next sprint · 🟡 Backlog

---

## #5 — Client-side filter breaks pagination in Users page

**Severity:** 🔴  
**Layer:** Frontend  
**File:** `src/pages/Users.tsx`

The `filteredUsers` computed value applies an `is_active` filter in the browser after the server has already paginated. This causes `total` in the server response to be incorrect relative to the displayed count — the pagination component shows the wrong number of pages.

**Fix:** Remove the client-side `is_active` filter. Pass `is_active` as a query param to the backend instead and let the server filter. The `GET /api/v1/users` endpoint already supports server-side filtering.

---

## #6 — Missing `AccessBanner` in Charges feature for secretary role

**Severity:** 🟠  
**Layer:** Frontend  
**File:** `src/features/charges/hooks/useChargesPage.ts`

When a secretary lacks permission to perform a charge action, the hook returns `false` silently instead of surfacing `<AccessBanner>`. This is inconsistent with the project UX contract (see `FRONTEND_PROJECT_RULES.md` §8.2).

**Fix:** Return `<AccessBanner>` component state (or a flag that the page uses to render it) when the role check fails, matching the pattern used in other feature hooks.

---

## #7 — Search query fires with no active filters

**Severity:** 🟠  
**Layer:** Frontend  
**File:** `src/features/search/hooks/useSearchPage.ts`

The `useQuery` call has no `enabled` guard. When the page mounts with no filters active, a request is sent to `GET /api/v1/search` with empty params. The UI handles it with an empty state, but the request is wasteful and adds server load.

**Fix:** Add `enabled: hasAnyFilter` where `hasAnyFilter` checks whether at least one filter param is non-empty.

---

## #8 — Auth expiry flag reset via `setTimeout` is brittle

**Severity:** 🟠  
**Layer:** Frontend  
**File:** `src/api/client.ts`

The `isHandlingAuthExpiry` global flag is reset via `setTimeout(..., 5000)`. Under concurrent 401 responses the flag may reset prematurely, allowing duplicate `AUTH_EXPIRED_EVENT` dispatches and multiple redirect loops.

**Fix:** Replace the `setTimeout` reset with a ref-count or AbortController pattern that clears only when all in-flight requests have resolved.

---

## #9 — XLSX upload has no file size limit

**Severity:** 🟠  
**Layer:** Backend  
**File:** `app/clients/api/clients_excel.py`

`contents = await file.read()` reads the entire uploaded file into memory with no prior size check. A large or malicious file can cause OOM.

**Fix:** Read `Content-Length` header or stream the first N bytes before full read. Reject files above a reasonable ceiling (e.g. 10 MB) with HTTP 413 before calling `file.read()`.

---

## #10 — Generic `Exception` in VAT export leaks internal details

**Severity:** 🟠  
**Layer:** Backend  
**File:** `app/vat_reports/api/routes_client_summary.py`

```python
except Exception as exc:
    raise HTTPException(500, detail=f"Export failed: {exc}")
```

`str(exc)` may include file paths, stack frames, or library internals.

**Fix:** Log the full exception with `logger.exception(...)`, then raise with a generic message: `detail="Export failed. Please try again."`.

---

## #11 — ORM monkeypatching in annual reports

**Severity:** 🟡  
**Layer:** Backend  
**File:** `app/annual_reports/services/base.py`

```python
r.client_name = id_to_name.get(r.client_id)  # type: ignore[attr-defined]
```

Setting ad-hoc attributes on ORM instances is fragile — SQLAlchemy may discard them on refresh, and the pattern propagates through the codebase.

**Fix:** Project to a Pydantic response schema that explicitly includes `client_name: Optional[str]` and populate it at construction time rather than mutating the ORM object.

---

## #12 — Background jobs not scheduled

**Severity:** 🟡 (known gap)  
**Layer:** Backend  
**Files:** `app/signature_requests/services/` · `app/reminders/`

`SignatureRequest.expire_overdue()` and reminder dispatch both exist as service methods but are never called automatically. No scheduler (APScheduler, Celery, cron) is configured.

**Fix:** Wire an external scheduler (e.g. APScheduler in-process or a cron job) to call these methods daily. Jobs must remain idempotent per `BACKEND_PROJECT_RULES.md §2`.

---

## #13 — `void` suppresses errors in mutation `onSuccess`

**Severity:** 🟡  
**Layer:** Frontend  
**File:** `src/features/users/hooks/useUsersPage.ts`

```typescript
onSuccess: () => { void invalidateUsers(queryClient); }
```

Using `void` swallows any rejection from `invalidateUsers`. If invalidation fails silently, the UI shows stale data without any error.

**Fix:** Make `onSuccess` async and `await` the call:

```typescript
onSuccess: async () => { await invalidateUsers(queryClient); }
```

---

## #14 — Duplicate storage key constant

**Severity:** 🟡  
**Layer:** Frontend  
**Files:** `src/api/client.ts` · `src/store/auth.store.ts`

`AUTH_PERSIST_STORAGE_KEY` (in `client.ts`) and `AUTH_STORAGE_NAME` (in `auth.store.ts`) are the same string literal defined in two places. If one is changed, the other silently diverges and auth state becomes unreadable.

**Fix:** Export a single constant from one file and import it in the other.

---

## #15 — `utcnow()` duplicated in test utility

**Severity:** 🟡  
**Layer:** Backend  
**Files:** `app/utils/time.py` · `tests/services/annual_report_enums.py`

`utcnow()` is implemented twice. The test file defines its own copy instead of importing from `app/utils/time`.

**Fix:** Remove the duplicate definition and add `from app.utils.time import utcnow` to the test file.

---

## #16 — Partial version pinning in `requirements.txt`

**Severity:** 🟡  
**Layer:** Backend  
**File:** `requirements.txt`

Several packages use floor constraints (`>=`) or no version at all:

```
gunicorn          # no version
openpyxl>=3.1.0
reportlab>=4.0.0
requests>=2.31.0
psycopg2-binary>=2.9
```

In production, `pip install` may resolve a later version that introduces breaking changes.

**Fix:** Pin all packages to exact versions (`==`). Use `requirements.lock.txt` (which already exists and is fully pinned) as the source of truth for production installs, or consolidate both files.

---

## #17 — Circular import workaround in `notifications.py`

**Severity:** 🟡  
**Layer:** Backend  
**File:** `app/infrastructure/notifications.py`

```python
def __init__(self) -> None:
    from app.config import config  # local import to avoid circular
```

The local import inside `__init__` is a symptom of a circular dependency between `infrastructure` and `config`. This pattern hides the structural problem.

**Fix:** Resolve the circular dependency at the module level — typically by injecting config values as constructor parameters rather than importing the config module directly inside the class.

---

## Cross-cutting items (no single owner)

| Item | Severity | Note |
|---|---|---|
| No rate limiting on any endpoint | 🟠 | Any public or authenticated route can be hammered. Add middleware-level throttling. |
| No MFA for user accounts | 🟡 | Noted in `BACKEND_SPEC.md §16`. Out of scope until auth sprint. |
| No self-service password change | 🟡 | Noted in `BACKEND_SPEC.md §16`. |
| Notification channels are stubs | 🟡 | WhatsApp unimplemented; email via SendGrid gated by `NOTIFICATIONS_ENABLED`. |
| No scheduled expiry for `SignatureRequest` | 🟡 | See #12 above. |
| Aging report: no CSV format, no streaming | 🟡 | Excel and PDF only; full result set loaded before write. |
| Mixed search: no full-text or indexed search | 🟡 | `ilike` only; will not scale past ~100k rows. |
