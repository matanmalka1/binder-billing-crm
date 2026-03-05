# TODO — Code Review Issues

> Issues 1–4 have been resolved. This file tracks the remaining open items.
> Severity: 🔴 Fix ASAP · 🟠 Next sprint · 🟡 Backlog

---


## #8 — Auth expiry flag reset via `setTimeout` is brittle

**Severity:** 🟠  
**Layer:** Frontend  
**File:** `src/api/client.ts`

The `isHandlingAuthExpiry` global flag is reset via `setTimeout(..., 5000)`. Under concurrent 401 responses the flag may reset prematurely, allowing duplicate `AUTH_EXPIRED_EVENT` dispatches and multiple redirect loops.

**Fix:** Replace the `setTimeout` reset with a ref-count or AbortController pattern that clears only when all in-flight requests have resolved.

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
