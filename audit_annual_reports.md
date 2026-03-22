# Annual Reports Domain Audit

Audited: `app/annual_reports/` — all Python files
Date: 2026-03-22

---

## 1. Model ↔ Schema ↔ Repo ↔ Service ↔ API Sync

### 🔴 Blocking

**`services/financial_tax_service.py:18-21` — References non-existent `AnnualReportDetail` fields**
`detail.credit_points`, `detail.pension_credit_points`, `detail.life_insurance_credit_points`, `detail.tuition_credit_points` are all accessed but **none of these columns exist** on the `AnnualReportDetail` model (which only has `pension_contribution`, `donation_amount`, `other_credits`, `client_approved_at`, `internal_notes`, `amendment_reason`).
Fix: Add these columns to `annual_report_detail.py` and create an Alembic migration, or remove the credit-point breakdown logic and use only `other_credits`.

**`services/query_service.py:82-83` — References non-existent `AnnualReportDetail` fields**
`detail.tax_refund_amount` and `detail.tax_due_amount` are accessed but these fields do **not exist** on `AnnualReportDetail`. The model has `assessment_amount`, `refund_due`, `tax_due` on the parent `AnnualReport`, not on `AnnualReportDetail`.
Fix: Use `report.refund_due` / `report.tax_due` from the ORM report object, not from `detail`.

**`services/financial_tax_service.py:88` — References non-existent `AnnualReportDetail` fields**
`detail.tax_due_amount` and `detail.tax_refund_amount` referenced in readiness check — same missing-field problem.
Fix: Same as above.

**`services/annual_report_pdf_service.py:313-314` — References non-existent `AnnualReportDetail` fields**
`detail.tax_refund_amount` and `detail.tax_due_amount` accessed for PDF summary section — field names don't exist on model.
Fix: Use `report.refund_due` / `report.tax_due`.

**`services/tax_engine.py:76-78` — Syntax error — unreachable/broken `raise` statement**
```python
raise AppError(
    f"Tax year {tax_year} is not supported. Supported years: {sorted(_BRACKETS_BY_YEAR)}"
    "TAX_ENGINE.INVALID_INPUT", status_code=400)
```
The first string and the second string `"TAX_ENGINE.INVALID_INPUT"` are being concatenated (implicit string concatenation) instead of being passed as two separate arguments. `AppError` receives one concatenated string as `message` and `status_code=400` as keyword arg, but the `code` argument is lost. This is a malformed call.
Fix: Add a comma after the f-string so `"TAX_ENGINE.INVALID_INPUT"` becomes the `code` argument.

**`repositories/status_history_repository.py:22` — Model/Repo mismatch on `changed_by_name`**
`append_status_history` passes `changed_by_name` to the `AnnualReportStatusHistory` ORM constructor, but that model has no `changed_by_name` column. The model only has `changed_by` (FK to users). This will raise an `InvalidRequestError` at runtime.
Fix: Remove `changed_by_name` from the model constructor call, or add the column to the model + migration.

**`repositories/report_lifecycle_repository.py:37-44` — Duplicate `soft_delete` method**
`AnnualReportLifecycleRepository` defines `soft_delete` independently **without** checking `deleted_at.is_(None)` first (line 38: `filter(AnnualReport.id == report_id).first()` — no `deleted_at` filter). `AnnualReportReportRepository` also defines `soft_delete`. The facade merges both via MRO, so only one wins — the MRO winner (`AnnualReportReportRepository`) correctly calls `self.get_by_id` which filters soft-deleted records; but the lifecycle version would re-delete already-deleted records.
Fix: Remove `soft_delete` from `AnnualReportLifecycleRepository` entirely.

### 🟡 Should Fix

**`schemas/annual_report_responses.py:29-31` — `assessment_amount`, `refund_due`, `tax_due` typed as `float` not `Decimal`**
The ORM uses `Numeric(14,2)` (mapped to `Decimal`). All three fields are typed `Optional[float]` in `AnnualReportResponse`. This loses precision silently for large tax amounts.
Fix: Use `Optional[Decimal]` consistent with `StatusTransitionRequest` which already uses `Decimal`.

**`schemas/annual_report_responses.py:93-97` — `AnnualReportDetailResponse` has `total_income`, `total_expenses`, `taxable_income`, `profit`, `final_balance` typed as `float`**
Financial fields should use `Decimal` for precision. `profit` and `final_balance` are inconsistent with `FinancialSummaryResponse` which uses `Decimal`.
Fix: Change to `Optional[Decimal]` and align types.

**`schemas/annual_report_responses.py:100-113` — `SeasonSummaryResponse` missing `amended` field**
`AnnualReportStatus` has an `AMENDED` status but `SeasonSummaryResponse` has no `amended` field. `get_season_summary` in the repo calculates counts for all statuses, but the response schema silently drops the `amended` count.
Fix: Add `amended: int = 0` field.

**`services/base.py:30` — `id_to_name` uses `b.full_name` but `Business` model likely exposes a different attribute**
The `Business` model has `business_name` and may have `full_name` via a related `Client`. In `query_service.py:135`, `b.business_name or b.client.full_name` is used — both usages are inconsistent. `base.py:30` uses `b.full_name` which may not exist on `Business` directly and would silently return `None`.
Fix: Align to a single accessor, e.g. `b.full_name` if guaranteed, or use the same pattern as `query_service.py:135`.

**`schemas/annual_report_responses.py:44` — `available_actions: list[dict]` — untyped dict**
Other domains define typed action schemas. Using bare `dict` bypasses Pydantic validation.
Fix: Define a typed `ActionItem` schema or use `list[Any]`.

**`schemas/annual_report_detail.py` — `ReportDetailResponse` includes `credit_points` list but `AnnualReportDetail` model does not have a `credit_points` relationship**
`ReportDetailResponse.credit_points: list[CreditPointResponse]` — but `AnnualReportDetail` has no ORM relationship to `AnnualReportCreditPoint`. Calling `model_validate(detail)` will always produce an empty list rather than the real credit points. The credit points are queried and managed nowhere in the detail service.
Fix: Either wire a SQLAlchemy relationship on `AnnualReportDetail` → `AnnualReportCreditPoint`, or add a separate credit point endpoint.

**`models/annual_report_enums.py` — `SubmissionMethod.REPRESENTATIVE` comment says "מייצגים (שע"מ)" but `ONLINE` says "שידור ישיר"**
These are functionally the same system. Consider collapsing or clarifying the enum values.

---

## 2. Layer Separation

### 🟡 Should Fix

**`services/query_service.py:89-101` — Raw ORM query inside Service layer**
```python
advances_paid = sum(
    (p.paid_amount or Decimal("0"))
    for p in self.db.query(AdvancePayment).filter(...).all()
)
```
Direct `self.db.query(AdvancePayment)` in a service method violates the Service→Repository boundary. There is a dedicated `AdvancePaymentRepository` available.
Fix: Call `self.advance_repo.sum_paid_by_business_year(...)` (which already exists in `financial_tax_service.py:31`).

**`services/advances_summary_service.py:25-34` — Raw ORM query in service**
Same pattern — `self.db.query(AdvancePayment).filter(...)` directly in `AnnualReportAdvancesSummaryService`. `AdvancePaymentRepository` should be used instead.
Fix: Inject `AdvancePaymentRepository` and call the repo method.

**`services/financial_crud_service.py:27,67` — `BusinessRepository` instantiated inline in service**
```python
business = BusinessRepository(self.db).get_by_id(report.business_id)
```
Instantiating repositories inline inside service methods is an anti-pattern. The base service should wire this once.
Fix: Add `self.business_repo = BusinessRepository(db)` to `FinancialBaseService.__init__`.

### 🔵 Suggestion

**`services/query_service.py:130-166` — `kanban_view` belongs in `kanban_service.py`**
The `kanban_view` method is defined in `query_service.py` but the Kanban-specific service is `kanban_service.py`. `AnnualReportKanbanService` only has `transition_stage`. Moving `kanban_view` to `kanban_service.py` aligns responsibility.

---

## 3. Duplicate Code

### 🟡 Should Fix

**`services/query_service.py:89-101` vs `services/advances_summary_service.py:25-34` — Duplicate advance payment aggregation logic**
Both compute paid advance payments for a `business_id`/`tax_year` pair with the same filter. The logic exists a third time in `financial_tax_service.py:31` (using `advance_repo.sum_paid_by_business_year`). Two of three usages bypass the repo.
Fix: Consolidate all three to use `advance_repo.sum_paid_by_business_year`.

**`services/status_service.py` vs `services/query_service.py` — `_cancel_pending_signature_requests` called from two different mixins**
`_cancel_pending_signature_requests` is defined in `status_service.py` but also called from `query_service.py:127`. Since both are mixins of `AnnualReportService`, this works via inheritance, but the method belongs conceptually in `base.py` so its location is visible to all mixins. Currently it lives in `status_service.py` which creates a hidden cross-mixin dependency.
Fix: Move `_cancel_pending_signature_requests` and `_trigger_signature_request` to `base.py`.

**`services/financial_base_service.py:15-21` — `_SCHEDULE_LABELS` duplicates the schedule names from `models/annual_report_enums.py`**
Schedule labels exist both in `FinancialBaseService._SCHEDULE_LABELS` and as comments in `AnnualReportSchedule` enum. The PDF service also has separate `_INCOME_LABELS` / `_EXPENSE_LABELS` / `_STATUS_LABELS` / `_CLIENT_TYPE_LABELS` dicts. Three separate places translate enum values to Hebrew strings.
Fix: Centralize all label dicts in `services/labels.py` (or `constants.py`) and import from there.

---

## 4. File Naming

### 🟡 Should Fix

**`repositories/report_repository.py` — Confusing name; actually named `AnnualReportReportRepository`**
The file is `report_repository.py` and the class is `AnnualReportReportRepository` — the "Report" suffix is doubled. This is the primary CRUD repo for `AnnualReport` model.
Fix: Rename file to `annual_report_crud_repository.py` and class to `AnnualReportCrudRepository`.

**`repositories/detail/repository.py` — Unnecessarily nested directory**
A single file `detail/repository.py` inside a subdirectory for a single class. No other domain does this. It complicates imports.
Fix: Move to `repositories/detail_repository.py` and remove the `detail/` subdirectory.

**`services/query_service.py` — Name doesn't reflect full scope**
This file contains `get_detail_report`, `amend_report`, and `kanban_view` — none of which are pure queries. It has effectively become a catch-all service mixin.
Fix: Extract `amend_report` to `status_service.py` and `kanban_view` to `kanban_service.py`. Rename to `annual_report_read_service.py`.

### 🔵 Suggestion

**`services/base.py` — Generic name**
Consider `annual_report_base_service.py` consistent with all other service files in this domain.

---

## 5. Global Extraction

### 🔵 Suggestion

**`services/tax_engine.py` and `services/ni_engine.py` — Domain-independent Israeli tax calculation engines**
These are pure calculation modules with no domain ORM dependencies. `calculate_tax` and `calculate_national_insurance` could be used by other domains (e.g. `vat_reports`, `advance_payments`). Both already import only from `app.core.exceptions`.
Suggest: Move to `app/utils/israeli_tax/` or `app/core/tax_engine.py` + `app/core/ni_engine.py`.

**`services/deadlines.py` — Israeli statutory deadline logic**
`standard_deadline` (April 30) and `extended_deadline` (January 31) are Israeli income tax law constants. `tax_deadline` domain likely needs the same logic.
Suggest: Move to `app/utils/israeli_deadlines.py` for cross-domain use.

**`models/annual_report_expense_line.py:29-38` — `STATUTORY_RECOGNITION_RATES` — Israeli tax rule constants in model file**
Business-logic constants (`VEHICLE: 0.75`, `COMMUNICATION: 0.80`) embedded in the model file violate layer separation (models should be pure ORM declarations).
Suggest: Move `STATUTORY_RECOGNITION_RATES`, `DEFAULT_RECOGNITION_RATE`, and `default_recognition_rate` to `services/constants.py`.

---

## 6. Constants

### 🟡 Should Fix

**`services/tax_engine.py:7-32` — 2026 brackets are identical to 2025 brackets**
```python
2026: [
    (84_120, 0.10),
    (120_720, 0.14),
    ...
```
Using 2025 values as 2026 placeholders is appropriate only if confirmed — but there is no comment documenting this as intentional. When the ITA publishes 2026 brackets, this silently uses stale data.
Fix: Add an explicit comment: `# PLACEHOLDER — update when ITA publishes 2026 brackets`.

**`services/tax_engine.py:40` — Magic constant `_DONATION_CREDIT_RATE = 0.35`**
The 35% donation credit rate is an Israeli tax law constant. It is currently documented by name but lives alongside runtime code.
Fix: Move to `constants.py` with a comment referencing Section 46 of the Income Tax Ordinance.

**`services/ni_engine.py:11-12` — NI rates as bare module-level floats**
`_NI_RATE_BASE = 0.0597` and `_NI_RATE_HIGH = 0.1783` are Israeli statutory rates with no source citation.
Fix: Add comments referencing the specific NI regulation/year, and move to `constants.py`.

**`services/tax_engine.py:34-38` — `_CREDIT_POINT_VALUE_BY_YEAR` uses 2026 = 2025 value**
Same issue as brackets — 2026 credit point value is identical to 2025 (3,003 NIS). Add a placeholder comment.

**`repositories/report_lifecycle_repository.py:60` — `stale_days: int = 7, limit: int = 3` — magic defaults**
`list_stuck_reports` defaults are unexplained. `limit=3` is especially arbitrary for a production list method.
Fix: Extract to constants in `constants.py` with documentation.

### 🔵 Suggestion

**`services/kanban_service.py:6-12` — `STAGE_TO_STATUS` dict — consider moving to `constants.py`**
This mapping is domain logic and should be co-located with `VALID_TRANSITIONS` and `FORM_MAP` in `constants.py`.

---

## 7. File Size

### 🟡 Should Fix

**`services/annual_report_pdf_service.py` — 344 lines (exceeds 150-line limit)**
The file contains two logical units: the `AnnualReportPdfService` class and a 200-line `_build_pdf` function with embedded table helpers.
Fix: Split into:
- `annual_report_pdf_service.py` — service class only (~30 lines)
- `annual_report_pdf_builder.py` — `_build_pdf` and helper functions (~200 lines)

**`services/query_service.py` — 167 lines (exceeds 150-line limit)**
As noted in section 4, this file's scope has grown beyond queries. Extracting `amend_report` and `kanban_view` would reduce it to ~100 lines.

**`services/financial_crud_service.py` — 123 lines** — within limit but approaching it.

---

## 8. Completeness

### 🔴 Blocking

**`api/annual_report_create_read.py:92` — `HTTPException` used instead of domain exception**
```python
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="הדוח לא נמצא")
```
Other 404 cases use `NotFoundError`. Using raw `HTTPException` bypasses the centralized error handler and may produce a different response shape.
Fix: Use `raise NotFoundError("הדוח לא נמצא", "ANNUAL_REPORT.NOT_FOUND")` or let the service raise it.

**`api/annual_report_create_read.py:106` — Same `HTTPException` pattern for delete 404**
Fix: Same as above.

### 🟡 Should Fix

**`api/annual_report_schedule.py` — No delete endpoint for schedules**
Schedules can be added and completed but not removed. A wrongly added schedule blocks submission (readiness check).
Fix: Add `DELETE /{report_id}/schedules/{schedule}` restricted to `ADVISOR`.

**`services/query_service.py:45-46` — `get_season_summary` returns raw dict, not typed response**
The method returns `dict` (from repo), bypassing Pydantic validation. The season endpoint works because `AnnualReportSeasonService.get_season_summary_response` wraps it, but the raw `get_season_summary` exposure is unsafe.
Fix: Remove `get_season_summary` from `AnnualReportQueryService` or type the return.

**`api/annual_report_business.py` — `list_business_reports` is unbounded**
`service.get_business_reports(business_id)` calls `repo.list_by_business` which has no pagination. A client with many tax years will return all records.
Fix: Add optional `page`/`page_size` params; use the paginated `list_all` pattern.

**`models/annual_report_credit_point_reason.py` — `AnnualReportCreditPoint` has no CRUD repo or service**
The model exists, the schema exists (`CreditPointResponse`, `CreditPointCreateRequest`, `CreditPointUpdateRequest`), but there is no repository and no API endpoint for managing credit points. The `ReportDetailResponse` includes `credit_points: list[CreditPointResponse]` but it is always empty.
Fix: Implement `AnnualReportCreditPointRepository` and CRUD endpoints, or remove the model/schema if not in scope.

**`api/annual_report_status.py:52-72` — `submit_report` endpoint duplicates `transition_status`**
`POST /{report_id}/submit` internally calls `transition_status` with `new_status="submitted"`. `POST /{report_id}/status` already accepts `status=submitted`. Two routes do the same thing with different request shapes.
Fix: Deprecate or document the distinction clearly; consider removing the `/submit` route.

**`services/create_service.py:104` — Status history note contains `TBD` (English) for custom deadlines**
```python
f"... מועד אחרון: {filing_deadline.strftime('%d/%m/%Y') if filing_deadline else 'TBD'}"
```
`TBD` is English; the note should be in Hebrew.
Fix: Use `"לא נקבע"` instead of `"TBD"`.

---

## 9. Dead Code

### 🟡 Should Fix

**`models/annual_report_expense_line.py:3` — `from decimal import Decimal` unused at module level after class definition**
`Decimal` is used in the `STATUTORY_RECOGNITION_RATES` dict and `default_recognition_rate` function — so it is not truly unused — but `from enum import Enum as PyEnum` on line 3 is unused (the class inherits from `str, PyEnum` but `PyEnum` comes from the import).
Actually `PyEnum` IS used on line 13 (`class ExpenseCategoryType(str, PyEnum)`). However `from sqlalchemy.orm import relationship` on line 8 IS used on line 59. No dead imports here.

**`models/annual_report_income_line.py:3` — `from enum import Enum as PyEnum` — `PyEnum` used only in class definition**
This is fine but worth noting: the pattern `class IncomeSourceType(str, PyEnum)` can be simplified to `class IncomeSourceType(str, Enum)` using the already-imported alias. No action required.

**`models/annual_report_annex_data.py:3` — `from enum import Enum as PyEnum` unused**
`PyEnum` is imported but never referenced in this file. `AnnualReportSchedule` is imported from enums directly.
Fix: Remove the unused `from enum import Enum as PyEnum` import.

**`services/query_service.py:4-5` — Unused imports**
`from sqlalchemy import func` and `from app.core.exceptions import ConflictError` are imported. `ConflictError` is used at line 113 (in `amend_report`). `func` is used at line 98. Both are actually used.

**`services/detail_service.py:5` — `from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError`**
Only `NotFoundError` is used in this file. `AppError`, `ConflictError`, and `ForbiddenError` are dead imports.
Fix: Remove unused imports.

**`services/kanban_service.py` — `STAGE_TO_STATUS` does not include `post_submission` or `transmitted` correctly**
`STAGE_TO_STATUS` maps `transmitted → submitted` only. If a report is `accepted` or `closed`, those statuses map to `TRANSMITTED` in the Kanban view but there is no reverse mapping — so `transition_stage("transmitted")` forces the report to `submitted` regardless of whether it was `accepted` or `closed`. The dict is incomplete for backwards-navigation.
Fix: Document the intentional one-way nature, or expand the mapping.

---

## 10. Pagination

### 🟡 Should Fix

**`repositories/report_repository.py:55-61` — `list_by_business` is unbounded**
No pagination on `list_by_business`. Returns all records for a `business_id`. Used by `get_business_reports` in API.
Fix: Add `page`/`page_size` and call `self._paginate(q, page, page_size)`.

**`repositories/report_lifecycle_repository.py:15-35` — `list_overdue` is unbounded**
No pagination limit. A large firm could have hundreds of overdue reports. The API endpoint `/overdue` returns all of them.
Fix: Add `page`/`page_size` parameters and paginate.

**`repositories/report_lifecycle_repository.py:78-88` — `get_season_summary` fetches all records in Python**
Loads all `AnnualReport` rows for a `tax_year` into memory to count by status. As volume grows this is inefficient.
Fix: Use `GROUP BY status` SQL aggregation with `func.count`.

**`api/annual_report_season.py:24` — `page_size` default is 50, not 20**
Project convention requires `page_size=20` as default. The season endpoint uses 50.
Fix: Change `Query(50, ge=1, le=200)` to `Query(20, ge=1, le=200)`.

**`repositories/report_repository.py:69` — `list_by_status` default `page_size=50`, not 20**
Fix: Change to `page_size: int = 20`.

**`repositories/report_repository.py:94` — `list_by_tax_year` default `page_size=50`, not 20**
Fix: Change to `page_size: int = 20`.

**`repositories/report_repository.py:113` — `list_all` default `page_size=50`, not 20**
Fix: Change to `page_size: int = 20`.

---

## 11. Israeli Domain Logic

### 🟡 Should Fix

**`services/deadlines.py:9-11` — `extended_deadline` returns January 31 of `tax_year + 2`**
The docstring says "January 31 two years after the tax year" — which is the CPA authorized-representative extension. However the standard extended deadline per Israeli ITA practice is typically January 31 of `tax_year + 1` (i.e., 9 months after the tax year ends). The "two years" variant is an exceptional extension. This should be explicitly documented and verified.
Fix: Add inline comment citing the specific ITA regulation/circular this is based on.

**`services/ni_engine.py:11-12` — NI rate split missing health insurance component**
Israeli BI+NI combined rate for self-employed (עצמאי) is 17.83% above ceiling and 5.97% below — but this is the combined Bituach Leumi + Bituach Briut (health insurance) rate. For employees, the rate structure differs. The engine applies a flat rate regardless of client type (individual vs self-employed vs employee). For `INDIVIDUAL` and `SALARY` income types the NI calculation should differ.
Fix: Add `client_type` parameter to `calculate_national_insurance` and branch the rate.

**`services/tax_engine.py:66` — `credit_points: float = 2.25` — hardcoded resident minimum**
The default credit point count is 2.25 (Israeli resident base). The function `get_tax_calculation` in `financial_tax_service.py` accumulates credit points from `detail.credit_points + detail.pension_credit_points + ...` but these fields do not exist (see Section 1). In practice, only the 2.25 resident base is ever used.
Fix: After fixing the `AnnualReportDetail` field issue, ensure the resident credit points (2.25) are always included and not accidentally double-counted.

**`models/annual_report_enums.py:37-47` — `AnnualReportSchedule` missing `SCHEDULE_A` from automatic generation**
`SCHEDULE_A` (חישוב הכנסה מעסק) is defined in the enum but not in `SCHEDULE_FLAGS` in `constants.py`. Self-employed and partnership filers (forms 1215) always require Schedule A. It is never auto-generated.
Fix: Add `("client_type_is_self_employed", AnnualReportSchedule.SCHEDULE_A)` logic to auto-generation, or add a flag to `AnnualReportCreateRequest`.

**`services/deadlines.py:4-7` — `standard_deadline` — does not account for April 30 falling on Shabbat/holiday**
Per Israeli law, when the deadline falls on Shabbat or a Jewish holiday, it moves to the next business day. The current implementation always returns April 30.
Fix: Document this known limitation and note it as a Sprint 10+ item.

**`models/annual_report_expense_line.py:29-31` — `VEHICLE: 0.75` recognition rate**
Israeli tax rules allow 25% of vehicle expenses for non-mixed-use vehicles (i.e., 75% deductible), but this 0.75 rate applies only to passenger vehicles. Commercial vehicles are 100% deductible. The static rate does not accommodate this distinction.
Fix: Add a note or add a `vehicle_type` field to expense lines.

---

## 12. Response Consistency

### 🟡 Should Fix

**`api/annual_report_create_read.py` vs other domains — `business_id` used consistently; no `client_id` drift**
The domain correctly uses `business_id` throughout. No drift detected. ✅

**`schemas/annual_report_responses.py` vs `schemas/annual_report_detail.py` — Overlapping detail fields in two response schemas**
`AnnualReportDetailResponse` (in `annual_report_responses.py`) duplicates `pension_contribution`, `donation_amount`, `other_credits`, `client_approved_at`, `internal_notes`, `amendment_reason` from `ReportDetailResponse` (in `annual_report_detail.py`). Two separate schemas represent the same sub-object. Consumers must know which endpoint returns which schema.
Fix: `AnnualReportDetailResponse` should embed `ReportDetailResponse` instead of duplicating fields.

**`schemas/annual_report_financials.py:92-99` — `FinancialSummaryResponse` uses `Decimal` for totals; `AnnualReportDetailResponse` uses `float` for the same totals**
`total_income`, `total_expenses`, `taxable_income` are `Decimal` in `FinancialSummaryResponse` but `float` in `AnnualReportDetailResponse`. The API returns different types for the same data depending on which endpoint the client calls.
Fix: Standardize to `Decimal` in both.

**`services/query_service.py:77-79` — Taxable income computed as `total_income - total_expenses` (gross)**
Taxable income in `get_detail_report` subtracts `total_expenses` (gross), but in `get_financial_summary` (via `financial_crud_service.py:111`) it correctly subtracts `recognized_expenses`. The two "taxable_income" figures will differ when recognition rates < 1.
Fix: Use `recognized_expenses` in `get_detail_report` taxable income computation.

---

## 13. Authorization

### 🟡 Should Fix

**`api/annual_report_status.py:24-49` — `transition_status` endpoint allows SECRETARY to change status**
The router-level dependency allows `ADVISOR | SECRETARY`. Status transitions include moving to `SUBMITTED`, `ACCEPTED`, `CLOSED` — high-stakes actions. At minimum `SUBMITTED` and `CLOSED` transitions should be `ADVISOR`-only.
Fix: Add `dependencies=[Depends(require_role(UserRole.ADVISOR))]` to the `/{report_id}/status` endpoint, or check `new_status` in the service and restrict based on role passed from API.

**`api/annual_report_status.py:52-72` — `submit_report` endpoint allows SECRETARY**
`POST /{report_id}/submit` submits to the ITA. This should require `ADVISOR`.
Fix: Add `dependencies=[Depends(require_role(UserRole.ADVISOR))]`.

**`api/annual_report_financials.py:78-83` — `update_income_line` (PATCH) allows SECRETARY**
Write operations on financial data should be `ADVISOR`-only. Currently `SECRETARY` can modify income lines.
Fix: Add `ADVISOR`-only role restriction to income and expense PATCH endpoints.

**`api/annual_report_financials.py:111-116` — `update_expense_line` (PATCH) allows SECRETARY**
Same issue as above.

**`api/annual_report_schedule.py:20-41` — Schedule management (add/complete) allows SECRETARY**
Adding/completing schedules is a write operation that affects the readiness gate for filing. Should be `ADVISOR`-only.
Fix: Restrict to `ADVISOR`.

**`api/annual_report_status.py:75-96` — `update_deadline` allows SECRETARY**
Changing a filing deadline is a consequential action; restrict to `ADVISOR`.

**`api/annual_report_kanban.py:13-21` — `transition_stage` (Kanban) allows SECRETARY**
Stage transitions ultimately call `transition_status` which moves the report through legally significant states.
Fix: Restrict to `ADVISOR`.

### 🔵 Suggestion

**`api/annual_report_detail.py:29-40` — `update_annual_report_detail` (PATCH) allows SECRETARY**
Updating `client_approved_at` and `amendment_reason` via SECRETARY may be intentional (secretary captures client approval), but should be explicitly documented as a deliberate design choice.

---

## 14. Soft Delete Consistency

### 🟡 Should Fix

**`repositories/report_lifecycle_repository.py:37-44` — `soft_delete` without `deleted_at` guard**
As noted in Section 1, `AnnualReportLifecycleRepository.soft_delete` queries without `deleted_at.is_(None)`, allowing it to return already-deleted records and re-set `deleted_at`.
Fix: Remove the duplicate method; rely on `AnnualReportReportRepository.soft_delete` which uses `get_by_id` (correctly guarded).

**`repositories/annex_data_repository.py:72-78` — Hard delete on `AnnualReportAnnexData`**
`AnnualReportAnnexData` rows are physically deleted (`self.db.delete(row)`). There is no `deleted_at` field on this model. For audit purposes annex data should be preserved.
Fix: Either add `deleted_at` + `deleted_by` columns to `AnnualReportAnnexData` and migrate to soft delete, or document the intentional hard-delete behavior.

**`repositories/expense_repository.py:71-77` — Hard delete on `AnnualReportExpenseLine`**
Same issue — income/expense lines are physically deleted. Financial audit trails would be lost.
Fix: Add soft-delete fields or document as intentional.

**`repositories/income_repository.py:63-69` — Hard delete on `AnnualReportIncomeLine`**
Same as expense lines.

**`repositories/annex_data_repository.py:52-57` — `get_by_id` has no `deleted_at` filter**
Since the model has no `deleted_at` field, this is a consequence of the missing soft-delete implementation above.

---

## 15. Error Message Language

### 🔴 Blocking

**`services/tax_engine.py:76-77` — English error message surfaced to user**
```python
f"Tax year {tax_year} is not supported. Supported years: {sorted(_BRACKETS_BY_YEAR)}"
```
This message is returned to the UI via `AppError`. All user-facing messages must be in Hebrew.
Fix: Use `f"שנת מס {tax_year} אינה נתמכת. שנים נתמכות: {sorted(_BRACKETS_BY_YEAR)}"`.

### 🟡 Should Fix

**`services/schedule_service.py:21` — Error message says "לוח זמנים" for a schedule/annex**
"לוח זמנים" means "timetable/schedule" in the colloquial sense, but in Israeli tax context the correct term for these annexes is "נספח" (appendix/schedule). The error message at line 21 says `"לוח זמנים '{schedule}' לא נמצא בדוח {report_id}"` — should use "נספח" for consistency with the domain vocabulary.
Fix: Replace "לוח זמנים" with "נספח" in all schedule-related error messages.

**`services/schedule_service.py:31` — English list in Hebrew error message**
`raise AppError(f"לוח זמנים לא חוקי '{schedule}'. חוקיים: {valid}", ...)` — `{valid}` will produce a Python list of English enum values like `['annex_15', 'annex_867', ...]`. While the code string is exempt, embedding a raw Python list in a user-facing message is poor UX.
Fix: Join the values into a readable string or omit the list from the user-facing message.

**`services/create_service.py:43-44` — English list in Hebrew error message**
Same issue — `f"חוקיים: {sorted(valid_client_types)}"` embeds English enum values in a Hebrew message.
Fix: Join as comma-separated Hebrew descriptions, or omit the list.

**`services/status_service.py:40` — English status values listed in Hebrew error message**
`f"... חוקיים: {sorted(valid_statuses)}"` — same issue.
Fix: Map to Hebrew labels or omit the value list.

All `raise AppError/NotFoundError/ConflictError/ForbiddenError` messages reviewed — all primary messages are in Hebrew. The above are edge cases where English enum values leak into messages.

---

## Summary Table

| Category               | Status | Count |
| ---------------------- | ------ | ----- |
| Model↔Schema sync      | ❌     | 7     |
| Layer separation       | ⚠️     | 5     |
| Duplicate code         | ⚠️     | 3     |
| File naming            | ⚠️     | 4     |
| Global extraction      | ⚠️     | 3     |
| Constants              | ⚠️     | 5     |
| File size              | ⚠️     | 2     |
| Completeness           | ❌     | 7     |
| Dead code              | ⚠️     | 4     |
| Pagination             | ⚠️     | 6     |
| Israeli domain logic   | ⚠️     | 6     |
| Response consistency   | ⚠️     | 4     |
| Authorization          | ⚠️     | 7     |
| Soft delete            | ⚠️     | 5     |
| Error message language | ❌     | 5     |

**Legend:** ❌ = has 🔴 blocking issues · ⚠️ = has 🟡 should-fix issues · ✅ = clean

---

## Top Critical Findings

1. **🔴 Runtime crashes** — `financial_tax_service.py`, `query_service.py`, and `annual_report_pdf_service.py` all access `AnnualReportDetail` fields that do not exist on the model (`credit_points`, `pension_credit_points`, `life_insurance_credit_points`, `tuition_credit_points`, `tax_refund_amount`, `tax_due_amount`). These will raise `AttributeError` at runtime on any tax calculation or PDF export call.

2. **🔴 Status history broken** — `status_history_repository.py` passes `changed_by_name` to the `AnnualReportStatusHistory` ORM constructor, but that column does not exist in the model. Every status transition, report creation, and deadline update call will raise a SQLAlchemy `InvalidRequestError`.

3. **🔴 Syntax error in tax engine** — `tax_engine.py:76-78` has implicit string concatenation that mangles the `AppError` call, losing the error code argument. Additionally the message is in English.
