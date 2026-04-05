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
## 12. Data Integrity & Edge Cases
## 13. Security
## 14. Missing Features (Domain Completeness)
## [MEDIUM] Withholding tax (ניכוי מס במקור) not modeled
- **File:** (new domain needed: `app/withholding_tax/`)
- **Category:** Missing Feature
- **Issue:** Israeli businesses above threshold income must track withholding certificates (אישורי ניכוי במקור) issued and received; there is no model, service, or report for this, making annual reconciliation unsupported.
- **Fix:** Add a `withholding_tax` domain with models for certificates, a reconciliation report, and deadline tracking. Scope and prioritize as a new sprint item.

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
