# Annual Reports Domain

> Last audited: 2026-04-13

---

## Responsibilities

Manages the full lifecycle of Israeli annual income-tax reports, scoped **per client record** (legal entity). A report is not per business — it belongs to the client record (the tax-bearing entity).

Covers:
- Report creation with automatic schedule generation and deadline assignment
- Status workflow from `NOT_STARTED` through `CLOSED`, with enforced transitions
- Annex / schedule tracking (required ITA schedules per report)
- Income and expense line CRUD
- Tax (income tax + NI) and readiness calculation via pure-function engines
- Advances summary linked to the report via `client_record_id + tax_year`
- Kanban stage view and season-level aggregation
- Cross-domain sync: tax deadlines completed/reopened on status transition
- Signature request lifecycle around the `PENDING_CLIENT` status
- PDF export (working draft)

---

## Core Entities

| Entity | Table | Notes |
|---|---|---|
| `AnnualReport` | `annual_reports` | Root aggregate. One main annual return per `(client_record_id, tax_year)`. Soft-deleted. |
| `AnnualReportDetail` | `annual_report_details` | 1:1 extension. Metadata only: approval, notes, deductions, amendment reason. |
| `AnnualReportIncomeLine` | `annual_report_income_lines` | Income line items. Multiple types per report. |
| `AnnualReportExpenseLine` | `annual_report_expense_lines` | Expense lines with statutory recognition rates. |
| `AnnualReportScheduleEntry` | `annual_report_schedules` | Required ITA annexes (schedule B/Bet/Gimmel etc). Tracked for completion. |
| `AnnualReportAnnexData` | `annual_report_annex_data` | Flexible JSON data rows per schedule. |
| `AnnualReportStatusHistory` | `annual_report_status_history` | Append-only audit trail. |
| `AnnualReportCreditPoint` | `annual_report_credit_points` | Per-reason credit point records. Source of truth for credit-point aggregation. |

---

## Domain Enums

### `AnnualReportStatus` (full lifecycle)

```
NOT_STARTED → COLLECTING_DOCS → DOCS_COMPLETE → IN_PREPARATION → PENDING_CLIENT → SUBMITTED
                                                                                ↓
                                                                           ASSESSMENT_ISSUED → OBJECTION_FILED → CLOSED
                                                                                ↓
                                                                             ACCEPTED → CLOSED
                                                                                ↓
                                                                             AMENDED → (back to IN_PREPARATION or re-SUBMITTED)
```

Valid transitions are enforced in `services/constants.py::VALID_TRANSITIONS`. All transitions go through `transition_status()` which holds a row-level lock.

### `client_type` — filing profile of the main annual return

| Value | Form | Description |
|---|---|---|
| `INDIVIDUAL` | 1301 | יחיד |
| `SELF_EMPLOYED` | 1301 + נספח א' | עצמאי |
| `CORPORATION` | 1214 | חברה בע"מ |
| `PUBLIC_INSTITUTION` | 1215 | מלכ"ר / מוסד ציבורי |
| `PARTNERSHIP` | 1301 + 1504 | שותף בשותפות |
| `CONTROL_HOLDER` | 1301 | בעל שליטה, עם דדליין כמו חברות |
| `EXEMPT_DEALER` | 1301 | עוסק פטור / זעיר שנמצא בתוך זרימת דוח מלא |

The domain rule is one primary annual report per client and tax year. Supporting forms and annexes are tracked within the report rather than as separate primary reports.

Important scope clarification:
- This domain models full annual returns only.
- `0135` is intentionally outside `AnnualReportForm`, because it is not a full primary annual return in this domain.
- `6111` is intentionally outside `AnnualReportForm`, because it is an annex and not a primary annual return.
- `control_holder` and `exempt_dealer` are filing profiles that affect deadline/obligation analysis; they are not separate legal entities.
- `partnership` should be read operationally as "partner with partnership income", not as a partnership entity filing its own primary income-tax return.

### `FilingDeadlineType`

| Value | Date | Notes |
|---|---|---|
| `STANDARD` | Varies by profile | Individuals manual: 29.05, individuals online: 30.06, corporations/control holders: 31.07 |
| `EXTENDED` | January 31 of `tax_year + 2` | מייצגים — authorized representative extension |
| `CUSTOM` | None (free text note) | ITA-granted individual extension |

### `AnnualReportSchedule` — ITA annex codes

`SCHEDULE_A` (1320 business / profession), `SCHEDULE_B` (1321 property / rent / interest / dividends / occasional transactions), `SCHEDULE_GIMMEL` (1322 securities gains), `SCHEDULE_DALET` (1323/1324 foreign income / foreign tax), `FORM_150`, `FORM_1504`, `FORM_6111`, `FORM_1344`, plus additional supported forms `FORM_1399`, `FORM_1350`, `FORM_1327`, `FORM_1342`, `FORM_1343`, `FORM_1348`, `FORM_858`

---

## Flows

### Creation flow

1. Validate `client_record_id` exists
2. Validate `client_type` and `deadline_type`
3. Validate `assigned_to` user exists (if provided)
4. Check uniqueness: `(client_record_id, tax_year)` — raises `ConflictError` if a main annual return already exists
5. Derive `form_type` snapshot from `client_type` via `FORM_MAP`
6. Compute `filing_deadline` from `deadline_type` and `tax_year`
7. Persist `AnnualReport`
8. Auto-generate `AnnualReportScheduleEntry` rows from filing profile and income flags (`SELF_EMPLOYED/PARTNERSHIP → SCHEDULE_A`, `PARTNERSHIP → FORM_1504`, `has_rental_income → SCHEDULE_B`, etc.)
9. Append initial status history entry (`NOT_STARTED`)
10. Write entity audit log
11. Return full detail response

### Status transition flow

1. Fetch with row-level lock (`SELECT FOR UPDATE`)
2. Validate `new_status` is a known enum value
3. Validate `new_status ∈ VALID_TRANSITIONS[current_status]` — raises `AppError` otherwise
4. If transitioning to `SUBMITTED`: run readiness check (schedules complete, income present, tax saved, client approved) — raises `AppError` listing all issues
5. Persist status and any side-data (`submitted_at`, `ita_reference`, assessment fields)
6. Append status history
7. Write entity audit log
8. If leaving `PENDING_CLIENT`: cancel pending signature requests
9. If entering `PENDING_CLIENT`: cancel then re-trigger signature request
10. Sync tax deadline (complete/reopen) via `deadline_sync`
11. Return response

### Readiness check (gates SUBMITTED transition)

Four checks, each worth 25% completion:
1. All required schedules are `is_complete = True`
2. Total income > 0
3. `tax_due` or `refund_due` is persisted on the report (written via `save_tax_calculation`)
4. `AnnualReportDetail.client_approved_at` is set

### Tax calculation flow (on-demand, never auto-persisted)

1. Aggregate income lines → `total_income`
2. Aggregate expense lines with recognition rates → `recognized_expenses`
3. `taxable_income = total_income - recognized_expenses`
4. Aggregate credit points from `AnnualReportCreditPoint`
5. Run `tax_engine.calculate_tax()` — bracket-based Israeli income tax
6. Run `ni_engine.calculate_national_insurance()` — NI by client type
7. Fetch VAT balance (informational) and advance payments paid
8. Return `TaxCalculationResponse`

To persist results, advisor explicitly calls `POST /tax-calculation/save`. This sets `tax_due` or `refund_due` on the report and is required before submission.

### VAT auto-populate flow

1. Validate report exists and is in a pre-submission status
2. If lines already exist and `force=False`: raise `ConflictError`
3. If `force=True`: delete all existing income/expense lines
4. Aggregate VAT income by `(client_record_id, tax_year)` → create one `BUSINESS` income line
5. Aggregate VAT expense categories → merge into annual report expense categories → create lines
6. Return creation summary

### Deadline sync (triggered on every status transition)

When a report enters a "filed" status (`SUBMITTED`, `ACCEPTED`, `ASSESSMENT_ISSUED`, `OBJECTION_FILED`, `CLOSED`): find matching `ANNUAL_REPORT` tax deadlines in `tax_year + 1` and mark them `COMPLETED`.

When leaving a filed status (amend/rollback): reopen the tax deadline and recreate reminder if none exists.

---

## Invariants (non-negotiable rules)

- **One main annual report per `(client_record_id, tax_year)`** — enforced by partial unique index and `ConflictError` in service. Soft-deleted reports are excluded from the constraint.
- **Status transitions are strictly gated** — no direct status writes outside `transition_status()`. All transitions use `VALID_TRANSITIONS`.
- **Submission requires readiness** — `transition_status(SUBMITTED)` always calls `_assert_filing_readiness()`.
- **Row-level lock on status transitions** — `get_by_id_for_update()` prevents concurrent status changes.
- **Annual reports are client-record-scoped** — `client_record_id` is the primary ownership key. Business references are optional context and are not the report scope.
- **Credit points come from rows, not cached columns** — aggregate from `AnnualReportCreditPoint` whenever tax or detail responses need them. `AnnualReportDetail` stores only metadata and deduction inputs.
- **Tax calculation is never auto-persisted** — `get_tax_calculation()` is always on-demand. `save_tax_calculation()` requires explicit advisor action.
- **Status history is append-only** — no updates or deletes on `AnnualReportStatusHistory`.
- **`changed_by_name` is a snapshot** — stored at transition time. Do not derive from users table retrospectively.

---

## Integration Points

| Domain | Direction | Purpose |
|---|---|---|
| `clients` | Inbound | Ownership, existence check, `full_name` resolution, status guards (CLOSED/FROZEN) |
| `users` | Inbound | RBAC (`require_role`), actor attribution |
| `signature_requests` | Outbound | Auto-create on `PENDING_CLIENT`, cancel on leaving |
| `advance_payments` | Outbound (read) | Advances paid by `(client_record_id, tax_year)` for balance computation |
| `vat_reports` | Outbound (read) | VAT net balance included in `TaxCalculationResponse`; VAT invoice aggregation for auto-populate |
| `tax_deadline` | Outbound (write) | Complete/reopen `ANNUAL_REPORT` deadline entries on status transitions |
| `reminders` | Outbound (write) | Create/cancel reminders when deadline is reopened |
| `permanent_documents` | Outbound (read) | Expense lines may reference supporting documents |
| `charge` | Outbound (read) | Informational — list charges linked to a report |
| `audit` | Outbound (write) | Entity audit log for create, status change, delete |
| `actions` | Inbound | Populates `available_actions` on report responses |

---

## Israeli Tax Law Notes

- **Income tax brackets**: Applied to `taxable_income = total_income - recognized_expenses - pension_deduction`. Brackets are indexed annually — see `tax_engine.py::_BRACKETS_BY_YEAR`.
- **Credit points**: Each credit point is worth a fixed annual monetary value (`_CREDIT_POINT_VALUE_BY_YEAR`). Standard resident entitlement is 2.25 points.
- **NI (ביטוח לאומי)**: Only applies to `SELF_EMPLOYED` and `PARTNERSHIP` — not `INDIVIDUAL` (employer withholds) and not `CORPORATION` (entity-level).
- **VAT is a separate obligation** — VAT net balance is informational in the tax summary, not part of the income-tax liability.
- **Donation credit (Section 46 ITO)**: 35% of qualifying donations. Minimum donation threshold applies before credit is granted.
- **Statutory recognition rates**: Vehicle expenses 75%, communication expenses 80% (Income Tax Regulations 28, 22).
- **ITA forms**: 1301 (individual / self-employed main return), 1214 (corporation main return), 1215 (public institution / nonprofit when relevant). `0135` stays outside this domain's primary-flow model, and `6111` stays an annex rather than a primary return.
- **Standard filing deadline**: Individuals manual 29.05, individuals online 30.06, corporations and control holders 31.07 of the following year. Extended (for authorized representatives): January 31 of the year after that.

---

## Known Limitations

These are intentional constraints — not bugs. Do not work around without a plan.

| Location | Limitation | Behavior |
|---|---|---|
| `query_service.py::kanban_view` | No pagination — loads all reports | No cap currently. |
| `vat_import_service.py::auto_populate` | Aggregates by `client_record_id`, merges all businesses | Incorrect for clients with multiple businesses. |
| `status_signature_helper.py` | Resolves business from first non-deleted business of client | Silent skip if client has no businesses |

---

## API Reference

All routes under `/api/v1/`. All require at minimum `SECRETARY` role unless noted.

### Core

| Method | Path | Role | Purpose |
|---|---|---|---|
| `POST` | `/annual-reports` | ADVISOR, SECRETARY | Create report |
| `GET` | `/annual-reports` | ADVISOR, SECRETARY | List all (paginated, filterable by tax_year) |
| `GET` | `/annual-reports/kanban/view` | ADVISOR, SECRETARY | Kanban grouped by stage |
| `GET` | `/annual-reports/overdue` | ADVISOR, SECRETARY | Open reports past deadline |
| `GET` | `/annual-reports/{id}` | ADVISOR, SECRETARY | Full detail |
| `DELETE` | `/annual-reports/{id}` | ADVISOR | Soft-delete |
| `POST` | `/annual-reports/{id}/amend` | ADVISOR | Transition SUBMITTED → AMENDED |

### Status & Workflow

| Method | Path | Role | Purpose |
|---|---|---|---|
| `POST` | `/{id}/status` | ADVISOR | Generic status transition |
| `POST` | `/{id}/submit` | ADVISOR | Submit with ITA reference |
| `POST` | `/{id}/deadline` | ADVISOR | Update deadline type |
| `POST` | `/{id}/transition` | ADVISOR | Kanban stage transition |
| `GET` | `/{id}/history` | ADVISOR, SECRETARY | Status history |

### Financial

| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/{id}/financials` | ADVISOR, SECRETARY | Income/expense lines + taxable income |
| `GET` | `/{id}/tax-calculation` | ADVISOR, SECRETARY | Full tax + NI calculation (on-demand) |
| `POST` | `/{id}/tax-calculation/save` | ADVISOR | Persist tax_due / refund_due |
| `GET` | `/{id}/advances-summary` | ADVISOR, SECRETARY | Advance payments and final balance |
| `GET` | `/{id}/readiness` | ADVISOR, SECRETARY | Filing readiness check |
| `POST` | `/{id}/auto-populate` | ADVISOR | Import income/expenses from VAT data |
| `GET` | `/{id}/charges` | ADVISOR, SECRETARY | Charges linked to the report |
| `GET` | `/{id}/export/pdf` | ADVISOR, SECRETARY | Working-draft PDF export |
| `POST` | `/{id}/income` | ADVISOR, SECRETARY | Add income line |
| `PATCH` | `/{id}/income/{line_id}` | ADVISOR | Update income line |
| `DELETE` | `/{id}/income/{line_id}` | ADVISOR | Delete income line |
| `POST` | `/{id}/expenses` | ADVISOR, SECRETARY | Add expense line |
| `PATCH` | `/{id}/expenses/{line_id}` | ADVISOR | Update expense line |
| `DELETE` | `/{id}/expenses/{line_id}` | ADVISOR | Delete expense line |

### Detail & Schedules

| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/{id}/details` | ADVISOR, SECRETARY | Detail fields (deductions, approval, notes) |
| `PATCH` | `/{id}/details` | ADVISOR, SECRETARY | Update detail fields |
| `GET` | `/{id}/schedules` | ADVISOR, SECRETARY | List required schedules |
| `POST` | `/{id}/schedules` | ADVISOR | Add schedule |
| `POST` | `/{id}/schedules/complete` | ADVISOR | Mark schedule complete |
| `GET` | `/{id}/annex/{schedule}` | ADVISOR, SECRETARY | Annex data lines |
| `POST` | `/{id}/annex/{schedule}` | ADVISOR, SECRETARY | Add annex line |
| `PATCH` | `/{id}/annex/{schedule}/{line_id}` | ADVISOR, SECRETARY | Update annex line |
| `DELETE` | `/{id}/annex/{schedule}/{line_id}` | ADVISOR | Delete annex line |

### Cross-prefix

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/clients/{client_record_id}/annual-reports` | List reports for a client record |
| `GET` | `/tax-year/{year}/reports` | Reports by tax year |
| `GET` | `/tax-year/{year}/summary` | Season summary |

---

## Tests

```bash
JWT_SECRET=test-secret pytest -q tests/annual_reports
```

---

## Open Tasks

Issues found during 2026-04-13 audit, ordered by severity:

- [x] **[HIGH]** `submission_method` and `extension_reason` are accepted in create/submit requests but never persisted — forward both to `repo.create()` and `repo.update()` in `create_service.py` and `status_service.py`
- [x] **[HIGH]** `deadline_sync.py` calls `db.commit()` inside a side-effect function — remove the explicit commit; let the outer transaction commit at request boundary
- [x] **[HIGH]** `amend_report()` in `query_service.py` bypasses `transition_status()` — no row-level lock, no entity audit log; route amend through `transition_status(AMENDED, ...)`
- [ ] **[HIGH]** Signature request silently not created when client has no businesses — raise `AppError` instead of silently returning; fix wrong scoping (report is client-scoped but SR is business-scoped)
- [ ] **[HIGH]** `total_liability` incorrectly adds VAT balance to income-tax liability — remove `vat_balance` from the sum in `financial_tax_service.py:54`; show VAT balance as a separate informational field
- [ ] **[HIGH]** 2026 NI ceiling in `ni_engine.py` is `622_920` — likely a data entry error; verify against 2026 NII circular and correct
- [ ] **[HIGH]** 2026 tax brackets in `tax_engine.py` show 5th-bracket ceiling lower than 2025 — verify against 2026 ITA circular; consider removing 2026 until confirmed
- [ ] **[HIGH]** `readiness_check` uses stale persisted `tax_due/refund_due` as the "tax saved" gate, but income/expense mutations don't trigger `invalidate_tax_if_open` — wire income/expense add/update/delete through the invalidation path
- [ ] **[HIGH]** `VatImportService.auto_populate` aggregates VAT by `client_record_id`, mixing all businesses — require explicit `business_id` or guard against multi-business clients
- [ ] **[MEDIUM]** `get_detail_report` fetches the same report three times — consolidate to one fetch
- [ ] **[MEDIUM]** `kanban_view()` has no cap — add `_KANBAN_REPORT_LIMIT` and document the architectural debt
- [ ] **[MEDIUM]** `business_name` field in `AnnualReportResponse` is always set to `client.full_name` — remove the field or set to `None`; annual reports are client-scoped
- [ ] **[MEDIUM]** `advances_summary_service.py` and `get_detail_report` both compute final balance independently and can diverge — consolidate
- [ ] **[MEDIUM]** `invalidate_tax_if_open` calls `get_by_client_year()` which returns only one report — for clients with multiple report types per year, only one is invalidated; use `list_by_client` and iterate
- [x] **[MEDIUM]** `AnnualReportScheduleEntry` uniqueness on `(annual_report_id, schedule)` is enforced in model + `0006_fix_annual_report_line_integrity`; duplicate schedules are deduplicated during migration and blocked at DB level
- [ ] **[MEDIUM]** `AnnualReportAnnexData.line_number` has no unique constraint per `(annual_report_id, schedule, line_number)` — concurrent inserts can collide; add constraint
- [ ] **[MEDIUM]** `deadline_sync.py` searches only in `tax_year + 1` for matching deadlines — EXTENDED deadline falls in `tax_year + 2`; expand range
- [ ] **[MEDIUM]** `DONATION_MINIMUM_ILS = 190` may be wrong — verify against current ITA Section 46 indexed amount (likely 180 ILS for 2024)
- [ ] **[LOW]** `AnnualReportDetail.updated_at` is `nullable=True` — change to `nullable=False, default=utcnow` and backfill via migration
- [ ] **[LOW]** `amend_report()` returns `get_detail_report()` which runs full financial recalculation — return `AnnualReportResponse` instead
- [ ] **[LOW]** `kanban_view()` uses hardcoded status strings instead of a reverse map from `STAGE_TO_STATUS` — extract to a `STATUS_TO_STAGE` constant in `constants.py`
