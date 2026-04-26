# Annual Reports Domain

> Last audited: 2026-04-21

---

## Responsibilities

Manages the full lifecycle of Israeli annual income-tax reports (`דוחות שנתיים`), scoped **per client record** (legal entity). A report belongs to the client record — not to a business.

Covers:
- Report creation with automatic schedule generation and deadline assignment
- Status workflow from `NOT_STARTED` through `CLOSED`, with strictly enforced transitions
- Annex / schedule tracking (required ITA schedules per report)
- Income and expense line CRUD with statutory recognition rates
- Tax (income tax + NI) and readiness calculation via pure-function engines
- Advances summary linked to the report via `client_record_id + tax_year`
- Season-level aggregation
- Cross-domain sync: tax deadlines completed/reopened on status transition
- Signature request lifecycle around the `PENDING_CLIENT` status
- PDF export (working draft)

---

## Core Entities

| Entity | Table | Notes |
|---|---|---|
| `AnnualReport` | `annual_reports` | Root aggregate. One per `(client_record_id, tax_year)`. Soft-deleted. |
| `AnnualReportDetail` | `annual_report_details` | 1:1 extension. Metadata only: approval, notes, deductions, amendment reason. |
| `AnnualReportIncomeLine` | `annual_report_income_lines` | Income line items by source type. Hard-deleted — no audit trail on remove. |
| `AnnualReportExpenseLine` | `annual_report_expense_lines` | Expense lines with statutory recognition rates. Hard-deleted. |
| `AnnualReportScheduleEntry` | `annual_report_schedules` | Required ITA annexes per filing profile. Unique per `(report, schedule)`. |
| `AnnualReportAnnexData` | `annual_report_annex_data` | Flexible JSON data rows per schedule line. Unique per `(schedule_entry, line_number)`. |
| `AnnualReportStatusHistory` | `annual_report_status_history` | Append-only audit trail. Never updated or deleted. |
| `AnnualReportCreditPoint` | `annual_report_credit_points` | Credit point rows by reason. Source of truth for all credit aggregation. |

---

## Domain Enums

### `AnnualReportStatus`

```
NOT_STARTED → COLLECTING_DOCS
COLLECTING_DOCS → DOCS_COMPLETE | NOT_STARTED
DOCS_COMPLETE → IN_PREPARATION | COLLECTING_DOCS
IN_PREPARATION → PENDING_CLIENT | DOCS_COMPLETE
PENDING_CLIENT → IN_PREPARATION | SUBMITTED
SUBMITTED → ACCEPTED | ASSESSMENT_ISSUED | AMENDED
AMENDED → IN_PREPARATION | SUBMITTED
ACCEPTED → CLOSED
ASSESSMENT_ISSUED → OBJECTION_FILED | CLOSED | PENDING_CLIENT | IN_PREPARATION | DOCS_COMPLETE
OBJECTION_FILED → CLOSED | DOCS_COMPLETE
CLOSED → (terminal)
```

All transitions enforced via `VALID_TRANSITIONS` in `services/constants.py`. All go through `transition_status()` which holds a row-level lock.

"Filed" statuses (used in deadline sync): `SUBMITTED`, `ACCEPTED`, `ASSESSMENT_ISSUED`, `OBJECTION_FILED`, `CLOSED`.

### `ClientAnnualFilingType` — filing profile

| Value | Form | Notes |
|---|---|---|
| `INDIVIDUAL` | 1301 | יחיד |
| `SELF_EMPLOYED` | 1301 + Schedule A | עצמאי — NI applies |
| `CORPORATION` | 1214 | חברה בע"מ — deadline July 31 |
| `PUBLIC_INSTITUTION` | 1215 | מלכ"ר |
| `PARTNERSHIP` | 1301 + 1504 | שותף — NI applies |
| `CONTROL_HOLDER` | 1301 | בעל שליטה — deadline July 31 |
| `EXEMPT_DEALER` | 1301 | עוסק פטור — in full-return workflow |

Scope clarifications:
- `0135` is not modeled — not a full primary annual return.
- `6111` is an annex, not a primary return.
- `PARTNERSHIP` means "partner with partnership income", not a partnership entity filing its own return.

### `FilingDeadlineType`

| Value | Date | Notes |
|---|---|---|
| `STANDARD` | Varies by profile | Individual manual: 29.05, individual online: 30.06, corp/control-holder: 31.07 of following year |
| `EXTENDED` | January 31 of `tax_year + 2` | מייצגים extension |
| `CUSTOM` | None (free text note) | ITA-granted individual extension |

### `AnnualReportSchedule`

`SCHEDULE_A`, `SCHEDULE_B`, `SCHEDULE_GIMMEL`, `SCHEDULE_DALET`, `FORM_150`, `FORM_1504`, `FORM_6111`, `FORM_1344`, `FORM_1399`, `FORM_1350`, `FORM_1327`, `FORM_1342`, `FORM_1343`, `FORM_1348`, `FORM_858`

---

## Flows

### Creation

1. Validate `client_record_id` exists and is active
2. Validate `client_type`, `deadline_type`, and `assigned_to` user (if provided)
3. Check uniqueness: `(client_record_id, tax_year)` → `ConflictError` if non-deleted record exists
4. Derive `form_type` from `client_type` via `FORM_MAP`
5. Compute `filing_deadline` from `deadline_type` and `tax_year`
6. Persist `AnnualReport`
7. Auto-generate `AnnualReportScheduleEntry` rows from filing profile and income flags:
   - `SELF_EMPLOYED` → Schedule A
   - `PARTNERSHIP` → Schedule A + Form 1504
   - `has_rental_income` → Schedule B
   - `has_capital_gains` → Schedule Gimmel
   - `has_foreign_income` → Schedule Dalet
8. Append initial status history (`NOT_STARTED`)
9. Write entity audit log
10. Return full detail response

### Status Transition

1. Fetch with row-level lock (`SELECT FOR UPDATE`)
2. Validate `new_status` is in `VALID_TRANSITIONS[current_status]`
3. If transitioning to `SUBMITTED`: run readiness check — raises `AppError` listing all failing gates
4. Persist status and any side-data (`submitted_at`, `ita_reference`, assessment fields)
5. Append status history
6. Write entity audit log
7. If leaving `PENDING_CLIENT`: cancel pending signature requests
8. If entering `PENDING_CLIENT`: cancel then re-trigger signature request
9. Sync tax deadline via `deadline_sync.sync_annual_report_deadline()`

**Note on signature side-effect:** Signature creation runs inside the same transaction. A failure there rolls back the entire status transition.

### Readiness Check (gates `SUBMITTED` transition)

Four gates, each worth 25% completion:
1. All required schedule entries have `is_complete = True`
2. Total income > 0
3. `tax_due` or `refund_due` is persisted (written via `save_tax_calculation`)
4. `AnnualReportDetail.client_approved_at` is set

### Tax Calculation (on-demand, never auto-persisted)

1. Aggregate income lines → `total_income`
2. Aggregate expense lines with recognition rates → `recognized_expenses`
3. `taxable_income = total_income - recognized_expenses`
4. Aggregate credit points from `AnnualReportCreditPoint` (default 2.25 resident points if no rows)
5. Run `tax_engine.calculate_tax()` — bracket-based Israeli income tax
6. Run `ni_engine.calculate_national_insurance()` — NI only for `SELF_EMPLOYED` and `PARTNERSHIP`
7. Fetch advance payments paid (read-only)
8. Return `TaxCalculationResponse`

To persist, advisor calls `POST /{id}/tax-calculation/save`. Explicitly required before submission.

Income/expense mutations clear `tax_due`/`refund_due` if report is pre-submission (`_invalidate_tax_if_open`).

### VAT Auto-Populate

1. Validate report exists and status is in `{NOT_STARTED, COLLECTING_DOCS, DOCS_COMPLETE, IN_PREPARATION}`
2. If lines exist and `force=False`: raise `ConflictError`
3. If `force=True`: delete all existing income/expense lines
4. Aggregate VAT income by `(client_record_id, tax_year)` → one `BUSINESS` income line
5. Aggregate VAT expenses by category → map to annual report categories → create lines
6. Return summary

### Deadline Sync (on every status transition)

Entering a filed status → find `ANNUAL_REPORT` tax deadlines in `tax_year + 1` and mark `COMPLETED`, cancel pending reminders.

Leaving a filed status → reopen deadline, create reminder if none exists.

---

## Invariants

- **One main report per `(client_record_id, tax_year)`** — partial unique index + `ConflictError`. Soft-deleted reports excluded.
- **Status transitions strictly gated** — no direct status writes; all go through `transition_status()` with `VALID_TRANSITIONS`.
- **Submission requires readiness** — `transition_status(SUBMITTED)` always calls `_assert_filing_readiness()`.
- **Row-level lock on all status transitions** — `get_by_id_for_update()`.
- **Reports are client-record-scoped** — `client_record_id` is the ownership key.
- **Credit points come from rows** — aggregate from `AnnualReportCreditPoint` always; never cached in detail columns.
- **Tax calculation is never auto-persisted** — `get_tax_calculation()` is read-only; `save_tax_calculation()` requires explicit advisor action.
- **Status history is append-only** — no updates or deletes on `AnnualReportStatusHistory`.
- **Status history actor is mandatory** — `changed_by` is required for every annual report status history row.

---

## Israeli Tax Law Notes

- **Income tax brackets**: Bracket-based on `taxable_income = total_income - recognized_expenses - pension_deduction`. Brackets indexed annually — see `tax_engine.py::_BRACKETS_BY_YEAR`.
- **Credit points**: Each point converts to a fixed monetary credit (`_CREDIT_POINT_VALUE_BY_YEAR`). Default resident entitlement: 2.25 points.
- **NI (ביטוח לאומי)**: Only applies to `SELF_EMPLOYED` and `PARTNERSHIP`. Returns 0 for `INDIVIDUAL` (employer-withheld) and `CORPORATION` (entity-level NI).
- **VAT is separate** — VAT net balance is informational in the tax summary, not part of income-tax liability.
- **Donation credit (Section 46 ITO)**: 35% of qualifying donations above 190 ILS minimum.
- **Statutory recognition rates**: Vehicle 75%, communication 80% (Income Tax Regulations 28, 22). All others 100%.

---

## Integration Points

| Domain | Direction | Purpose |
|---|---|---|
| `clients` | Inbound | Ownership check, active guard, `full_name` / `id_number` resolution |
| `users` | Inbound | RBAC, actor attribution |
| `signature_requests` | Outbound | Auto-create on `PENDING_CLIENT`, cancel on leaving — **runs inside status transaction** |
| `advance_payments` | Outbound (read) | Advances by `(client_record_id, tax_year)` for balance computation |
| `vat_reports` | Outbound (read) | VAT invoice aggregation for auto-populate; VAT balance in tax summary |
| `tax_deadline` | Outbound (write) | Complete/reopen `ANNUAL_REPORT` deadline entries on filed status changes |
| `reminders` | Outbound (write) | Create/cancel reminders on deadline reopen |
| `permanent_documents` | Outbound (read) | Expense line optional FK to supporting document |
| `charge` | Outbound (read) | List charges linked to report |
| `audit` | Outbound (write) | Entity audit log on create, status change, delete |
| `actions` | Inbound | Populates `available_actions` on report responses |

---

## API Reference

All routes under `/api/v1/`. Minimum role: `SECRETARY` unless noted.

### Core

| Method | Path | Role | Purpose |
|---|---|---|---|
| `POST` | `/annual-reports` | SECRETARY+ | Create report |
| `GET` | `/annual-reports` | SECRETARY+ | List all (paginated, filterable by tax_year) |
| `GET` | `/annual-reports/overdue` | SECRETARY+ | Open reports past deadline |
| `GET` | `/annual-reports/{id}` | SECRETARY+ | Full detail |
| `DELETE` | `/annual-reports/{id}` | ADVISOR | Soft-delete |
| `POST` | `/annual-reports/{id}/amend` | ADVISOR | Transition `SUBMITTED → AMENDED` |

### Status & Workflow

| Method | Path | Role | Purpose |
|---|---|---|---|
| `POST` | `/{id}/status` | ADVISOR | Generic status transition |
| `POST` | `/{id}/submit` | ADVISOR | Submit with ITA reference |
| `POST` | `/{id}/deadline` | ADVISOR | Update deadline type |
| `POST` | `/{id}/transition` | ADVISOR | Stage shortcut |
| `GET` | `/{id}/history` | SECRETARY+ | Status history |

### Financial

| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/{id}/financials` | SECRETARY+ | Income/expense lines + taxable income |
| `GET` | `/{id}/tax-calculation` | SECRETARY+ | Full tax + NI calculation (on-demand) |
| `POST` | `/{id}/tax-calculation/save` | ADVISOR | Persist `tax_due` / `refund_due` |
| `GET` | `/{id}/advances-summary` | SECRETARY+ | Advance payments and final balance |
| `GET` | `/{id}/readiness` | SECRETARY+ | Filing readiness check |
| `POST` | `/{id}/auto-populate` | ADVISOR | Import income/expenses from VAT data |
| `GET` | `/{id}/charges` | SECRETARY+ | Charges linked to report |
| `GET` | `/{id}/export/pdf` | SECRETARY+ | Working-draft PDF export |
| `POST` | `/{id}/income` | SECRETARY+ | Add income line |
| `PATCH` | `/{id}/income/{line_id}` | ADVISOR | Update income line |
| `DELETE` | `/{id}/income/{line_id}` | ADVISOR | Delete income line (hard delete) |
| `POST` | `/{id}/expenses` | SECRETARY+ | Add expense line |
| `PATCH` | `/{id}/expenses/{line_id}` | ADVISOR | Update expense line |
| `DELETE` | `/{id}/expenses/{line_id}` | ADVISOR | Delete expense line (hard delete) |

### Detail & Schedules

| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/{id}/details` | SECRETARY+ | Detail fields (deductions, approval, notes) |
| `PATCH` | `/{id}/details` | SECRETARY+ | Update detail fields |
| `GET` | `/{id}/schedules` | SECRETARY+ | List required schedules |
| `POST` | `/{id}/schedules` | SECRETARY+ | Add schedule |
| `POST` | `/{id}/schedules/complete` | ADVISOR | Mark schedule complete |
| `GET` | `/{id}/annex/{schedule}` | SECRETARY+ | Annex data lines |
| `POST` | `/{id}/annex/{schedule}` | SECRETARY+ | Add annex line |
| `PATCH` | `/{id}/annex/{schedule}/{line_id}` | SECRETARY+ | Update annex line |
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

## Known Limitations

Intentional constraints — do not work around without a plan.

| Location | Limitation | Behavior |
|---|---|---|
| `vat_import_service.py::auto_populate` | Aggregates VAT by `client_record_id`, merges all businesses | Incorrect for multi-business clients |
| `status_signature_helper.py` | Resolves business as first non-deleted business of client | Silent skip if client has no businesses |
| `deadline_sync.py` | Searches only `tax_year + 1` for matching deadlines | Misses EXTENDED deadlines that land in `tax_year + 2` |

---

## Open Tasks

Ordered by severity.

- [x] **[HIGH]** `submission_method` and `extension_reason` not persisted in create/submit — fixed in `create_service.py` and `status_service.py`
- [x] **[HIGH]** `deadline_sync.py` called `db.commit()` inside side-effect — removed; outer transaction commits at request boundary
- [x] **[HIGH]** `amend_report()` bypassed `transition_status()` — now routes through it (row-level lock, audit log)
- [x] **[MEDIUM]** `AnnualReportScheduleEntry` uniqueness on `(annual_report_id, schedule)` enforced in model and migration `0006`
- [ ] **[HIGH]** Signature request silently not created when client has no businesses — raise `AppError`; root cause: report is client-scoped but SR is business-scoped
- [ ] **[HIGH]** `total_liability` in `TaxCalculationResponse` adds VAT balance to income-tax liability — remove from sum; expose VAT balance as separate informational field
- [ ] **[HIGH]** 2026 NI ceiling in `ni_engine.py` is `622_920` — verify against 2026 NII circular
- [ ] **[HIGH]** 2026 tax brackets in `tax_engine.py` — 5th-bracket ceiling appears lower than 2025; verify against 2026 ITA circular
- [ ] **[HIGH]** Readiness check uses stale `tax_due/refund_due` — income/expense mutations already call `_invalidate_tax_if_open` but readiness gate still reads persisted values; ensure gate fails when values are cleared
- [ ] **[HIGH]** `VatImportService.auto_populate` aggregates by `client_record_id` — incorrect for multi-business clients; require explicit `business_id` or add guard
- [ ] **[MEDIUM]** `amend_report()` lives in `query_service.py` — write operation misplaced; move to `status_service.py`
- [ ] **[MEDIUM]** `business_name` in `AnnualReportResponse` always equals `client.full_name` — remove or set to `None`; annual reports are client-scoped, not business-scoped
- [ ] **[MEDIUM]** `advances_summary_service.py` and `get_detail_report` independently compute final balance — consolidate
- [ ] **[MEDIUM]** `AnnualReportAnnexData.line_number` — no unique constraint per `(annual_report_id, schedule, line_number)`; concurrent inserts can collide
- [ ] **[MEDIUM]** `DONATION_MINIMUM_ILS = 190` — verify against current ITA Section 46 indexed amount (may be 180 ILS for 2024)
- [ ] **[MEDIUM]** Signature creation runs inside the status transition transaction — failure rolls back the status change; decouple or wrap in try/except
- [ ] **[LOW]** `AnnualReportDetail.updated_at` is `nullable=True` — change to `nullable=False, default=utcnow` with backfill migration
