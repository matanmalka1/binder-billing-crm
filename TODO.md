# Backend TODO — Code Review Findings

> Generated from full dual-lens review (engineering + Israeli tax law).
> Sorted by severity within each section. Fix in order: CRITICAL → HIGH → MEDIUM → LOW.

---

## High Priority Focus

Top 10 most urgent tasks based on impact, dependencies, and current development risk.
- [ ] **[HIGH] Reminder not canceled when charge is marked paid** (`app/charge/services/billing_service.py:82-86`) — Reason: Advisors receive stale "unpaid charge" reminders for charges already marked paid, eroding trust in the notification system and causing unnecessary follow-up.
- [ ] **[HIGH] VatWorkItem unique constraint allows re-creation after soft-delete in PostgreSQL** (`app/vat_reports/models/vat_work_item.py:79`) — Reason: In production (PostgreSQL), soft-deleting a VAT period permanently blocks re-creation, silently making that period unfileable without manual DB intervention.
- [ ] **[HIGH] Annual report stuck in SUBMITTED if amendment needed** (`app/annual_reports/services/constants.py:17-57`) — Reason: A filed report that requires correction has no valid next state in the transition graph, requiring manual DB writes to proceed — blocking a normal legal workflow.
- [ ] **[HIGH] `assert_business_not_closed()` does not block FROZEN businesses** (`app/businesses/services/business_guards.py:19-25`) — Reason: Call sites that use the weaker guard instead of `assert_business_allows_create()` silently allow writes on FROZEN businesses, violating the core business-status invariant.

---

## 1. Domain Logic — VAT Reports
## 2. Domain Logic — Advance Payments
## 3. Domain Logic — Annual Reports
## 4. Domain Logic — Tax Deadlines
## 5. Domain Logic — Charge / Invoice
## 6. Domain Logic — Businesses

## [HIGH] `assert_business_not_closed()` does not block FROZEN businesses
- **File:** `app/businesses/services/business_guards.py:19-25`
- **Category:** Business Rule Gap
- **Issue:** `assert_business_not_closed()` only raises for CLOSED; callers that use this guard instead of `assert_business_allows_create()` silently permit write operations on FROZEN businesses.
- **Fix:** Audit every call site of `assert_business_not_closed()`; replace with `assert_business_allows_create()` where FROZEN should also be blocked, or document intentional FROZEN-allows-write exceptions per domain.

---

## 7. Domain Logic — Clients

---

## [MEDIUM] No client-level status gate — closed clients can get new businesses
- **File:** `app/businesses/services/business_service.py` (create path)
- **Category:** Business Rule Gap
- **Issue:** `Client` has no status field; a client with all CLOSED businesses can have new businesses created under them without any system-level warning.
- **Fix:** Add a check in `BusinessService.create()`: if all existing non-deleted businesses for this client are CLOSED, require explicit ADVISOR confirmation or warn. Alternatively, add `Client.status` column with its own guard.

---

## 8. Separation of Concerns

---

## [MEDIUM] Export format dispatch logic inside API router
- **File:** `app/vat_reports/api/routes_business_summary.py:44-57`
- **Category:** Business Logic in Router
- **Issue:** The export endpoint contains `if format == "excel": ... else: ...` branching and inline `try/except ImportError` — this is business logic that belongs in the service layer.
- **Fix:** Move format dispatch into `VatExportService.export(format, ...)`. The router calls one method and returns the result.

---

## [MEDIUM] `document_search_service` builds raw dicts (presentation in service)
- **File:** `app/search/services/document_search_service.py:20-35`
- **Category:** Separation of Concerns
- **Issue:** `search_documents()` constructs raw `dict` response objects with a `business_cache`; this is presentation/serialization logic that belongs in the router or schema layer.
- **Fix:** Return typed objects (ORM or dataclass); move dict construction to the router or a `DocumentSearchResult` schema with a `from_orm` factory.

---

## [x] [LOW] Service-layer constants file imports from model layer
- **File:** `app/annual_reports/services/constants.py:83-86`
- **Category:** Layer Violation
- **Issue:** `constants.py` imports `DEFAULT_RECOGNITION_RATE` and `STATUTORY_RECOGNITION_RATES` directly from `app.annual_reports.models.annual_report_expense_line` at the bottom of the file.
- **Fix:** Re-export these constants from `app/annual_reports/models/__init__.py` so services import from the models package boundary, not from a specific model file.

---


## 10. Redundant Code
## 11. Architectural Violations

---

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

---

## [HIGH] Advance payment status not auto-derived from paid_amount
- **File:** `app/advance_payments/services/advance_payment_service.py` (update path)
- **Category:** Missing Feature
- **Issue:** Updating `paid_amount` does not auto-set status to PAID or PARTIAL; advisors must manually update status, creating stale PENDING records.
- **Fix:** In `update_payment()`, after persisting `paid_amount`, derive status: `PAID` if `paid >= expected`, `PARTIAL` if `0 < paid < expected`, else `PENDING`.

---

## [HIGH] No VAT compliance reminder for missed filing periods
- **File:** `app/core/background_jobs.py` (new job needed)
- **Category:** Missing Feature
- **Issue:** The `vat_compliance` repository can identify overdue unfiled periods, but no background job fires reminders when a period passes its statutory deadline without a filed work item.
- **Fix:** Add a `daily_vat_compliance_job()` to `background_jobs.py` that queries `VatComplianceRepository` for past-deadline unfiled periods and creates reminders via `ReminderService`.

---

## [MEDIUM] Annual report filing deadline not auto-populated by entity type
- **File:** `app/annual_reports/services/` (create path)
- **Category:** Missing Feature
- **Issue:** `filing_deadline` is a free-write field; the system does not auto-populate it based on `client_type + tax_year` even though statutory deadlines are fixed by law (individuals: April 30; companies: November 30).
- **Fix:** On `AnnualReport` creation, derive `filing_deadline` from `FORM_MAP[client_type]` + `tax_year` using a `STATUTORY_DEADLINES` constant map; allow override but pre-fill.

---

## [MEDIUM] No warning when Osek Patur ceiling is approaching
- **File:** `app/vat_reports/services/data_entry_common.py:96-117`
- **Category:** Missing Feature
- **Issue:** `check_osek_patur_ceiling()` raises only when the ceiling is fully exceeded (100%); advisors have no advance warning to plan reclassification to Osek Murshe.
- **Fix:** Add a `WARNING` threshold at 80% of `OSEK_PATUR_CEILING_ILS` (≈98,266 ₪ for 2026); return a warning flag in the invoice create response when exceeded without blocking.

---

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

### Top 3 Priorities
1. **CRITICAL** — `vat_invoice_aggregation_repository.py:85`: add `deleted_at IS NULL` filter to Osek Patur ceiling query. One line. Ship now.
2. **CRITICAL** — Race condition on all status transitions: add `with_for_update()` to all fetch-then-transition patterns.
3. **HIGH** — Update 2026 tax brackets, credit point value, and NI ceiling from placeholders to actual ITA/NII-published values.

### Most Affected Domains
1. `annual_reports` — 7 issues
2. `vat_reports` — 5 issues
3. `charge` + `reminders` coupling — 3 issues

### Systemic Patterns to Address
- **Placeholders in production**: no CI gate prevents shipping `# PLACEHOLDER` tax constants.
- **Idempotency theater**: two bulk endpoints declare a header they never use.
- **One-directional event coupling**: reminders are created on charge/VAT events but never canceled on inverse events — needs a domain-event or callback pattern.
- **Float used for money**: `sum_vat_both_types`, `sum_net_both_types`, and the `net_vat` write path all cast `Decimal` → `float` before DB writes.
