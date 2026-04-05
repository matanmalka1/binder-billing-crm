# Backend TODO — Code Review Findings

> Generated from full dual-lens review (engineering + Israeli tax law).
> Sorted by severity within each section. Fix in order: CRITICAL → HIGH → MEDIUM → LOW.

---

## High Priority Focus

Top 10 most urgent tasks based on impact, dependencies, and current development risk.
- [ ] **[HIGH] Advance payment due-date formula wrong for companies (חברות)** (`app/advance_payments/services/advance_payment_generator.py:50-55`) — Reason: Companies are assigned a due date one month too late, causing all advance payment deadlines for חברות clients to be systemically wrong.
- [ ] **[HIGH] Reminder not canceled when charge is marked paid** (`app/charge/services/billing_service.py:82-86`) — Reason: Advisors receive stale "unpaid charge" reminders for charges already marked paid, eroding trust in the notification system and causing unnecessary follow-up.
- [ ] **[HIGH] VatWorkItem unique constraint allows re-creation after soft-delete in PostgreSQL** (`app/vat_reports/models/vat_work_item.py:79`) — Reason: In production (PostgreSQL), soft-deleting a VAT period permanently blocks re-creation, silently making that period unfileable without manual DB intervention.
- [ ] **[HIGH] Annual report stuck in SUBMITTED if amendment needed** (`app/annual_reports/services/constants.py:17-57`) — Reason: A filed report that requires correction has no valid next state in the transition graph, requiring manual DB writes to proceed — blocking a normal legal workflow.
- [ ] **[HIGH] `assert_business_not_closed()` does not block FROZEN businesses** (`app/businesses/services/business_guards.py:19-25`) — Reason: Call sites that use the weaker guard instead of `assert_business_allows_create()` silently allow writes on FROZEN businesses, violating the core business-status invariant.

---

## 1. Domain Logic — VAT Reports

---
## [x] [MEDIUM] "other" expense category silently yields 0% VAT deduction
- **File:** `app/vat_reports/services/constants.py` / `app/vat_reports/models/vat_enums.py` / frontend `constants.ts`
- **Category:** Business Rule Gap
- **Status:** ✅ RESOLVED
- **Fix Applied:** Removed `ExpenseCategory.OTHER` enum value entirely from backend and frontend. Invoices without a recognized category are now blocked by type validation.
- **Changes:**
  - Backend: `app/vat_reports/models/vat_enums.py` — removed `OTHER = "other"` from `ExpenseCategory` enum
  - Backend: `app/vat_reports/services/constants.py` — removed `"other"` label and `Decimal("0.0000")` deduction rate
  - Frontend: `src/features/vatReports/constants.ts` — removed `"other"` from `EXPENSE_CATEGORIES` array, `CATEGORY_LABELS`, `CATEGORY_COLORS`, and `DEDUCTION_RATES`

---

## [MEDIUM] VAT totals converted to float before DB write — precision loss
- **File:** `app/vat_reports/repositories/vat_invoice_aggregation_repository.py:35,46`
- **Category:** Wrong Logic
- **Issue:** `float(output_row or 0)` and `float(sum(...))` convert Decimal amounts to IEEE-754 floats before the values are written to `Numeric(14,2)` columns, introducing rounding errors (e.g., `1234.56 → 1234.5600000000002`).
- **Fix:** Return `Decimal` from both methods; remove all `float()` wrappers on monetary values throughout the VAT aggregation path.

---

## 2. Domain Logic — Advance Payments

---

## [HIGH] Advance payment due-date formula wrong for companies (חברות)
- **File:** `app/advance_payments/services/advance_payment_generator.py:50-55`
- **Category:** Wrong Logic
- **Issue:** Due date is always computed as the 15th of the month following the period end, which is correct for self-employed (עצמאי) but wrong for companies — companies file advances by the 15th of the *same* covered month.
- **Fix:** Branch on `business.business_type`: if `COMPANY`, set `due_date` to the 15th of the period's own month rather than the following month.

---

## [MEDIUM] VAT rate hardcoded in income reverse-calculation
- **File:** `app/advance_payments/services/advance_payment_calculator.py:11-18`
- **Category:** Missing Logic
- **Issue:** `derive_annual_income_from_vat()` divides by an assumed VAT rate that is either hardcoded or pulled from a non-versioned constant; if the rate changes, the derived income is silently wrong.
- **Fix:** Accept `vat_rate: Decimal` as an explicit parameter; callers should pass the current year's rate from a versioned constants table.

---

## [LOW] AdvancePaymentStatus.PARTIAL never set automatically
- **File:** `app/advance_payments/models/advance_payment.py`
- **Category:** Missing Logic
- **Issue:** The PARTIAL status exists but is never auto-set when `0 < paid_amount < expected_amount`; advisors must remember to update it manually.
- **Fix:** In `AdvancePaymentService.update_payment()`, after writing `paid_amount`, derive and write the correct status: PAID if `paid >= expected`, PARTIAL if `0 < paid < expected`, PENDING otherwise.

---

## 3. Domain Logic — Annual Reports

---



## [HIGH] 2026 National Insurance ceiling is a 2025 placeholder
- **File:** `app/annual_reports/services/ni_engine.py:10`
- **Category:** Wrong Logic
- **Issue:** `_NI_CEILING_BY_YEAR[2026] = 93_384.0` is the 2025 ceiling; NII publishes an updated ceiling annually.
- **Fix:** Update `_NI_CEILING_BY_YEAR[2026]` with the NII-published 2026 annual income ceiling.

---

## [HIGH] NI rates are self-employed only — wrong for employee reports
- **File:** `app/annual_reports/services/constants.py:77-78`
- **Category:** Potential Wrong Logic
- **Issue:** `NI_RATE_BASE = 0.0597` and `NI_RATE_HIGH = 0.1783` are the self-employed (עצמאי) rates; employees (שכירים) have different employee/employer split rates, but `ni_engine.py` uses a single pair regardless of `ClientTypeForReport`.
- **Fix:** Add a `client_type` parameter to `calculate_national_insurance()`; apply the employee rate schedule when `client_type == ClientTypeForReport.INDIVIDUAL` (with employment income flag).

---

## [MEDIUM] SUBMITTED → AMENDED transition missing from annual report state machine
- **File:** `app/annual_reports/services/constants.py:39-42`
- **Category:** Missing Logic / Data Integrity
- **Issue:** `VALID_TRANSITIONS` has no path from `SUBMITTED` to `AMENDED`; once a report is submitted it cannot legally move to amendment without manual DB intervention.
- **Fix:** Add `AnnualReportStatus.SUBMITTED: {AnnualReportStatus.AMENDED, ...existing targets...}` to `VALID_TRANSITIONS`.

---

## [LOW] Donation credit granted below legal minimum floor (190 ₪)
- **File:** `app/annual_reports/services/tax_engine.py:91` / `constants.py:73`
- **Category:** Wrong Logic
- **Issue:** `donation_credit = donation_amount * 0.35` is applied unconditionally; Israeli law (Section 46 ITO) requires the donation to exceed 190 ₪ before any credit is granted.
- **Fix:** Add `DONATION_MINIMUM_ILS = 190` constant; set `donation_credit = 0` when `donation_amount < DONATION_MINIMUM_ILS`.

---

## 4. Domain Logic — Tax Deadlines

---

## [MEDIUM] Deadline can be created for already-filed annual report
- **File:** `app/tax_deadline/services/tax_deadline_service.py`
- **Category:** Business Rule Gap
- **Issue:** No guard prevents creating a tax deadline for a `(business_id, tax_year)` that already has an `AnnualReport` in `SUBMITTED / ACCEPTED / CLOSED` status, polluting the work queue with irrelevant items.
- **Fix:** Before creating a deadline, query `AnnualReportRepository` for the same `(business_id, tax_year)` with a terminal status and raise or warn if found.

---

## 5. Domain Logic — Charge / Invoice

---

## [HIGH] Reminder not canceled when charge is marked paid
- **File:** `app/charge/services/billing_service.py:82-86`
- **Category:** Missing Logic
- **Issue:** `issue_charge()` creates an "unpaid charge" reminder with `days_unpaid=30`, but `mark_charge_paid()` never cancels it — advisors keep receiving stale reminders for paid charges indefinitely.
- **Fix:** In `mark_charge_paid()`, after `update_status()`, call `ReminderService(self.db).cancel_reminders_for_charge(charge_id)` (add this method to `ReminderService` if it doesn't exist).

---

## [MEDIUM] No path to soft-delete a canceled charge
- **File:** `app/charge/services/billing_service.py:148-168`
- **Category:** Business Rule Gap
- **Issue:** `delete_charge()` only accepts DRAFT charges; CANCELED charges cannot be removed from lists even if the cancellation was in error, leaving noise in the advisor's charge history.
- **Fix:** Either extend `delete_charge()` to also allow CANCELED status, or add a dedicated `delete_canceled_charge()` method with appropriate audit.

---

## 6. Domain Logic — Businesses

---

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

---

## [x] [MEDIUM] get_business_or_raise + assert_business_allows_create duplicated across 5+ services
- **File:** `app/charge/services/billing_service.py:37-38`, `app/advance_payments/services/advance_payment_service.py`, `app/vat_reports/services/intake.py:54-58`, and others
- **Category:** Redundant Code
- **Issue:** Every domain service that creates records repeats the same two-line guard sequence without a shared helper.
- **Fix:** Add `validate_business_for_create(db: Session, business_id: int) -> Business` to `app/businesses/services/business_guards.py` that calls both steps atomically; replace all call sites.

---

##  [x] [LOW] `sum_vat_both_types` and `sum_net_both_types` run redundant paired queries
- **File:** `app/vat_reports/repositories/vat_invoice_aggregation_repository.py:18-72`
- **Category:** Redundant Code
- **Issue:** Both methods fire two separate `func.sum` queries filtered by `invoice_type`; this can be one grouped query.
- **Fix:** Replace each pair with a single query `GROUP BY invoice_type` and unpack both results in one round-trip.

---

## 11. Architectural Violations

---

## [MEDIUM] Idempotency keys declared on bulk endpoints but never consumed
- **File:** `app/charge/api/charge.py:132`, `app/businesses/api/businesses.py:113`
- **Category:** Architectural Violation
- **Issue:** `X-Idempotency-Key` is a required header on two bulk endpoints but the value is never stored, checked, or used; re-sending the same request executes the operation again.
- **Fix:** Either implement idempotency (persist key + response hash, return cached response on replay) or remove the header requirement entirely — a declared-but-ignored guarantee is worse than none.

---

## 12. Data Integrity & Edge Cases

---


---

## [HIGH] VatWorkItem unique constraint allows re-creation after soft-delete in PostgreSQL
- **File:** `app/vat_reports/models/vat_work_item.py:79`
- **Category:** Data Integrity
- **Issue:** `UniqueConstraint("business_id", "period")` has no `postgresql_where` predicate; in PostgreSQL, a soft-deleted row for `(business_id=1, period="2025-01")` permanently blocks re-creation of that period.
- **Fix:** Add `postgresql_where=text("deleted_at IS NULL")` to the constraint, matching the pattern used in `annual_report_model.py`.

---

## [HIGH] Annual report stuck in SUBMITTED if amendment needed (no valid transition)
- **File:** `app/annual_reports/services/constants.py:17-57`
- **Category:** Data Integrity
- **Issue:** `VALID_TRANSITIONS[SUBMITTED]` has no path to `AMENDED`; once submitted, a report requiring correction has no programmatic next state and requires manual DB intervention.
- **Fix:** Add `AnnualReportStatus.AMENDED` to `VALID_TRANSITIONS[AnnualReportStatus.SUBMITTED]`. (Tracked also under §3.)

---

## [MEDIUM] Binder pickup notification always uses first business for multi-business clients
- **File:** `app/binders/services/binder_service.py:79-86`
- **Category:** Edge Case
- **Issue:** `mark_ready_for_pickup()` calls `business_repo.list_by_client()` and passes `businesses[0]` to `NotificationService`; if a client has multiple businesses the notification may reference the wrong one.
- **Fix:** Either add a `business_id` FK to `Binder` (preferred) or document this as a known limitation with a `TODO` comment.

---

## [LOW] `advance_payment.paid_amount` should default to 0, not NULL
- **File:** `app/advance_payments/models/advance_payment.py`
- **Category:** Nullable Semantics
- **Issue:** `paid_amount` is nullable; if `NULL`, the schema's computed `delta = expected - paid` will error or return wrong results.
- **Fix:** Set `server_default="0"` and `default=Decimal("0")` on the column, or add a `@validator` in the schema to coerce `None → 0`.

---

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
