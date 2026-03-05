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

## #12 — Background jobs not scheduled

**Severity:** 🟡 (known gap)  
**Layer:** Backend  
**Files:** `app/signature_requests/services/` · `app/reminders/`

`SignatureRequest.expire_overdue()` and reminder dispatch both exist as service methods but are never called automatically. No scheduler (APScheduler, Celery, cron) is configured.

**Fix:** Wire an external scheduler (e.g. APScheduler in-process or a cron job) to call these methods daily. Jobs must remain idempotent per `BACKEND_PROJECT_RULES.md §2`.




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
