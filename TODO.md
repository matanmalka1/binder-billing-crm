# Backend TODO — Code Review Findings

> Generated from full dual-lens review (engineering + Israeli tax law).
> Sorted by severity within each section. Fix in order: CRITICAL → HIGH → MEDIUM → LOW.

## High Priority Focus

Top 10 most urgent tasks based on impact, dependencies, and current development risk.
- [ ] **[HIGH] Reminder not canceled when charge is marked paid** (`app/charge/services/billing_service.py:82-86`) — Reason: Advisors receive stale "unpaid charge" reminders for charges already marked paid, eroding trust in the notification system and causing unnecessary follow-up.

## 1. Domain Logic — VAT Reports
## 2. Domain Logic — Advance Payments
## 3. Domain Logic — Annual Reports
## 4. Domain Logic — Tax Deadlines
## 5. Domain Logic — Charge / Invoice
## 6. Domain Logic — Businesses
## 7. Domain Logic — Clients
## 8. Separation of Concerns
## 10. Redundant Code
## 11. Architectural Violations

## [MEDIUM] Idempotency keys declared on bulk endpoints but never consumed
- **File:** `app/charge/api/charge.py:132`, `app/businesses/api/businesses.py:113`
- **Category:** Architectural Violation
- **Issue:** `X-Idempotency-Key` is a required header on two bulk endpoints but the value is never stored, checked, or used; re-sending the same request executes the operation again.
- **Fix:** Either implement idempotency (persist key + response hash, return cached response on replay) or remove the header requirement entirely — a declared-but-ignored guarantee is worse than none.

---

## 12. Data Integrity & Edge Cases


## [MEDIUM] Binder pickup notification always uses first business for multi-business clients
- **File:** `app/binders/services/binder_service.py:79-86`
- **Category:** Edge Case
- **Issue:** `mark_ready_for_pickup()` calls `business_repo.list_by_client()` and passes `businesses[0]` to `NotificationService`; if a client has multiple businesses the notification may reference the wrong one.
- **Fix:** Either add a `business_id` FK to `Binder` (preferred) or document this as a known limitation with a `TODO` comment.

## 13. Security

---

## [HIGH] Single-tenant IDOR — no resource-level ownership enforcement
- **File:** All API routers that accept `{business_id}` path param
- **Category:** Security / IDOR
- **Issue:** No service or router verifies that the requested `business_id` belongs to any scope tied to the authenticated user; any ADVISOR/SECRETARY can access any business by guessing its ID.
- **Fix:** This is intentional for a single-office system — document it explicitly in `CLAUDE.md` as a single-tenant design decision. If multi-tenancy is ever added, every service fetch must add a `business.office_id == current_user.office_id` scope check.

---

## [HIGH] Confirm `require_role` dependency chain always includes token_version check
- **File:** `app/users/api/deps.py:66-77`
- **Category:** Security
- **Issue:** If any route wires `Depends(require_role(...))` without transitively reaching `get_current_user`, the `token_version` invalidation check is bypassed.
- **Fix:** Run `grep -r "require_role" app/` and confirm every usage flows through `get_current_user`; if `require_role` itself calls `get_current_user` as a dependency parameter, this is already safe — verify and document.

---

## [MEDIUM] S3StorageProvider missing path traversal guard
- **File:** `app/infrastructure/storage.py`
- **Category:** Security
- **Issue:** `LocalStorageProvider` validates keys against path traversal; `S3StorageProvider` passes keys to `boto3` without validation — a crafted key with `../` could reach unintended R2 bucket prefixes.
- **Fix:** Add `if ".." in key or key.startswith("/"):  raise ValueError(...)` to `S3StorageProvider.upload()` and `delete()`.

---

## 14. Missing Features (Domain Completeness)


## [MEDIUM] Withholding tax (ניכוי מס במקור) not modeled
- **File:** (new domain needed: `app/withholding_tax/`)
- **Category:** Missing Feature
- **Issue:** Israeli businesses above threshold income must track withholding certificates (אישורי ניכוי במקור) issued and received; there is no model, service, or report for this, making annual reconciliation unsupported.
- **Fix:** Add a `withholding_tax` domain with models for certificates, a reconciliation report, and deadline tracking. Scope and prioritize as a new sprint item.

---

## [LOW] No audit trail for Business / Client / Charge / AnnualReport mutations
- **File:** Across `app/businesses/`, `app/clients/`, `app/charge/`, `app/annual_reports/`
- **Category:** Missing Feature
- **Issue:** User mutations are audited; VAT mutations are audited. But changes to business status, client data, charge amounts, and annual report fields have no audit trail.
- **Fix:** Add a generic `EntityAuditLog` model (entity_type, entity_id, field, old_value, new_value, actor, timestamp) and wire it into each domain's update service methods.

---

## [LOW] Signature request expiry TTL is hardcoded
- **File:** `app/core/background_jobs.py` / signature request models
- **Category:** Missing Feature
- **Issue:** The expiry TTL for signature requests is hardcoded; different document types may legitimately need different validity windows.
- **Fix:** Add a `expiry_days` column to `SignatureRequest` defaulting to the current hardcoded value; allow callers to override per document type.

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 2 |
| HIGH | 14 |
| MEDIUM | 14 |
| LOW | 10 |
| **Total** | **40** |

### Most Affected Domains
1. `annual_reports` — 7 issues
2. `vat_reports` — 5 issues
3. `charge` + `reminders` coupling — 3 issues

### Systemic Patterns to Address
- **Placeholders in production**: no CI gate prevents shipping `# PLACEHOLDER` tax constants.
- **Idempotency theater**: two bulk endpoints declare a header they never use.
- **One-directional event coupling**: reminders are created on charge/VAT events but never canceled on inverse events — needs a domain-event or callback pattern.
- **Float used for money**: `sum_vat_both_types`, `sum_net_both_types`, and the `net_vat` write path all cast `Decimal` → `float` before DB writes.
