# Advance Payments

> Owns client advance-tax payment records (`מקדמות`), annual schedule generation, and payment analytics.

---

## Responsibilities

- Store one active advance payment per client and period.
- Expose client-scoped CRUD, suggestion, KPI, and chart endpoints.
- Generate monthly or bi-monthly yearly schedules.
- Calculate suggested expected amounts from prior-year VAT and client advance rate.
- Aggregate overview and collection KPIs across clients.

---

## Entities

### `AdvancePayment`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `Integer` | PK |
| `client_id` | `Integer` | FK -> `clients.id`, indexed |
| `period` | `String(7)` | `YYYY-MM`, first month in the reporting period |
| `period_months_count` | `Integer` | `1` monthly, `2` bi-monthly |
| `due_date` | `Date` | Payment due date |
| `expected_amount` | `Numeric(10,2) \| null` | Expected payment amount |
| `paid_amount` | `Numeric(10,2)` | Defaults to `0` |
| `status` | `AdvancePaymentStatus` | Defaults to `pending` |
| `paid_at` | `DateTime \| null` | Actual payment timestamp |
| `payment_method` | `PaymentMethod \| null` | Payment channel |
| `annual_report_id` | `Integer \| null` | FK -> `annual_reports.id`, indexed |
| `notes` | `String(500) \| null` | Free text |
| `created_at` | `DateTime` | Defaults to `utcnow()` |
| `updated_at` | `DateTime \| null` | Updated on repository writes |
| `deleted_at` | `DateTime \| null` | Soft delete marker |
| `deleted_by` | `Integer \| null` | FK -> `users.id` |

Relationships declared via foreign keys:

- `client_id` -> `clients.id`
- `annual_report_id` -> `annual_reports.id`
- `deleted_by` -> `users.id`

Enums:

- `AdvancePaymentStatus`: `pending`, `paid`, `partial`, `overdue`
- `PaymentMethod`: `bank_transfer`, `credit_card`, `check`, `direct_debit`, `cash`, `other`

Indexes:

- Partial unique index on `client_id + period` where `deleted_at IS NULL`
- Secondary indexes on `client_id + period`, `status`, `due_date`

---

## Schemas

| Schema | Direction | Notes |
|--------|-----------|-------|
| `AdvancePaymentRow` | Response | Uses `from_attributes=True`; couples directly to ORM objects |
| `AdvancePaymentListResponse` | Response | Paginated list envelope |
| `AdvancePaymentCreateRequest` | Request | Validates `period` format, `period_months_count`, non-negative amounts, max `notes=500` |
| `AdvancePaymentUpdateRequest` | Request | Partial update payload; rejects empty body |
| `AdvancePaymentSuggestionResponse` | Response | Suggested amount + `has_data` |
| `AdvancePaymentOverviewRow` | Response | Uses `from_attributes=True`; couples directly to ORM objects |
| `AdvancePaymentOverviewResponse` | Response | Overview list + KPI totals |
| `AnnualKPIResponse` | Response | Client-level yearly KPI payload |
| `MonthlyChartRow` | Response | Monthly chart point |
| `ChartDataResponse` | Response | Client-level chart payload |
| `GenerateScheduleRequest` | Request | `year`, `period_months_count` |
| `GenerateScheduleResponse` | Response | Bulk generation counters |

Computed fields:

- `AdvancePaymentRow.delta = expected_amount - paid_amount`
- `AdvancePaymentOverviewRow.delta = expected_amount - paid_amount`

Shared API types:

- `ApiDecimal` serializes decimals as strings
- `ApiDateTime` normalizes datetimes to UTC ISO-8601 strings

---

## Services

### `AdvancePaymentService.list_payments_for_client(client_id, year=None, status=None, page=1, page_size=20) -> tuple[list[AdvancePayment], int]`

Checks that the client exists, defaults `year` to the current UTC year, and returns paginated payments for that client/year.

### `AdvancePaymentService.create_payment_for_client(client_id, period, period_months_count, due_date, expected_amount=None, paid_amount=None, payment_method=None, annual_report_id=None, notes=None) -> AdvancePayment`

Blocks creation for closed or frozen clients, rejects duplicate active periods, and inserts a new payment with initial `pending` status.

### `AdvancePaymentService.update_payment_for_client(client_id, payment_id, **fields) -> AdvancePayment`

Loads the client-scoped payment, filters allowed fields, derives `status` from `paid_amount` when `status` is not supplied, and persists the update.

### `AdvancePaymentService.delete_payment_for_client(client_id, payment_id, actor_id) -> None`

Loads the client-scoped payment and soft-deletes it by setting `deleted_at` and `deleted_by`.

### `AdvancePaymentService.suggest_expected_amount_for_client(client_id, year, period_months_count=1) -> Decimal | None`

Reads the client advance rate and prior-year VAT summary, derives annual income from VAT using `VAT_RATE`, and returns the rounded expected amount or `None` if data is missing.

### `AdvancePaymentAnalyticsService.list_overview(year, month=None, statuses=None, page=1, page_size=50) -> tuple[list[tuple[AdvancePayment, str, int]], int]`

Loads matching payments for the year/month/status filters, fetches client names, sorts rows by client name and period, and slices them for pagination.

### `AdvancePaymentAnalyticsService.get_annual_kpis_for_client(client_id, year) -> dict`

Validates that the client exists, loads yearly aggregates, and adds `client_id`, `year`, and `collection_rate`.

### `AdvancePaymentAnalyticsService.get_overview_kpis(year, month=None, statuses=None) -> dict`

Loads overview totals and adds `collection_rate`.

### `AdvancePaymentAnalyticsService.get_chart_data_for_client(client_id, year) -> dict`

Validates that the client exists and returns monthly expected, paid, and overdue amounts.

### `generate_annual_schedule(client_id, year, db, period_months_count=1) -> tuple[list[AdvancePayment], int]`

Generates monthly or bi-monthly periods for the year, skips periods that already exist, creates missing payments with due date on the 15th of the following month, and returns `(created_records, skipped_count)`.

### `derive_annual_income_from_vat(total_output_vat, vat_rate) -> Decimal`

Raises `AppError` when `vat_rate` is zero and otherwise calculates taxable annual income from VAT.

### `calculate_expected_amount(annual_income, advance_rate, period_months_count=1) -> Decimal`

Calculates `annual_income * advance_rate / 100 / 12 * period_months_count` and rounds to the nearest shekel.

---

## Repositories

### `AdvancePaymentRepository.create(...) -> AdvancePayment`

Creates and commits a new `AdvancePayment` row.

### `AdvancePaymentRepository.get_by_id(payment_id) -> AdvancePayment | None`

Returns one active payment by id.

### `AdvancePaymentRepository.get_by_id_for_client(payment_id, client_id) -> AdvancePayment | None`

Returns one active payment scoped to a client.

### `AdvancePaymentRepository.list_by_client_year(client_id, year, status=None, page=1, page_size=50) -> tuple[list[AdvancePayment], int]`

Filters active payments by client and `YYYY-%`, optionally filters by status, orders by period, and applies DB pagination.

### `AdvancePaymentRepository.exists_for_period(client_id, period) -> bool`

Checks whether an active payment already exists for the client and period.

### `AdvancePaymentRepository.update(payment, **fields) -> AdvancePayment`

Delegates field updates to `BaseRepository._update_entity(..., touch_updated_at=True)`.

### `AdvancePaymentRepository.soft_delete(payment_id, deleted_by) -> bool`

Marks a payment as deleted and commits.

### `AdvancePaymentRepository.list_overview_payments(year, month, statuses) -> list[AdvancePayment]`

Delegates overview payment loading to `AdvancePaymentAggregationRepository`.

### `AdvancePaymentRepository.sum_paid_by_client_year(client_id, year) -> float`

Delegates yearly paid sum aggregation to `AdvancePaymentAggregationRepository`.

### `AdvancePaymentRepository.get_collections_aggregates(year, month=None) -> list`

Delegates per-client collection aggregates to `AdvancePaymentAggregationRepository`.

### `AdvancePaymentAggregationRepository.list_overview_payments(year, month, statuses) -> list[AdvancePayment]`

Returns all active payments for the year, optionally filtered by month coverage and status.

### `AdvancePaymentAggregationRepository.sum_paid_by_client_year(client_id, year) -> float`

Returns the total `paid_amount` for `paid` payments in the client/year scope.

### `AdvancePaymentAggregationRepository.get_collections_aggregates(year, month=None) -> list`

Joins `clients` and returns per-client expected amount, paid amount, and overdue count aggregates. Contains a cross-domain repository import from `app.clients.models.client`.

### `AdvancePaymentAnalyticsRepository.get_annual_kpis_for_client(client_id, year) -> dict`

Groups the client’s payments by status and returns yearly totals plus overdue and paid counts.

### `AdvancePaymentAnalyticsRepository.get_overview_kpis(year, month, statuses) -> dict`

Returns overview totals for expected and paid amounts.

### `AdvancePaymentAnalyticsRepository.monthly_chart_data_for_client(client_id, year) -> list[dict]`

Returns grouped monthly chart rows with expected, paid, and overdue amounts.

Helper expressions:

- `advance_payment_status_text_expr()` normalizes enum status to lowercase text
- `advance_payment_start_month_expr()` extracts the month from `period`
- `advance_payment_matches_month_expr(month)` matches monthly and bi-monthly periods covering a given month

Raw SQL:

- No raw `SELECT/INSERT/UPDATE/DELETE` strings in repository methods

---

## API Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `GET` | `/clients/{client_id}/advance-payments` | `require_role(...)` | `ADVISOR`, `SECRETARY` | List client payments for a year with status filter and pagination |
| `POST` | `/clients/{client_id}/advance-payments` | `require_role(...)` | `ADVISOR` | Create a new advance payment |
| `GET` | `/clients/{client_id}/advance-payments/suggest` | `require_role(...)` | `ADVISOR`, `SECRETARY` | Suggest expected amount from prior-year VAT |
| `GET` | `/clients/{client_id}/advance-payments/kpi` | `require_role(...)` | `ADVISOR`, `SECRETARY` | Return annual KPIs for one client |
| `GET` | `/clients/{client_id}/advance-payments/chart` | `require_role(...)` | `ADVISOR`, `SECRETARY` | Return monthly chart data for one client |
| `PATCH` | `/clients/{client_id}/advance-payments/{payment_id}` | `require_role(...)` | `ADVISOR` | Update one client payment |
| `DELETE` | `/clients/{client_id}/advance-payments/{payment_id}` | `require_role(...)` | `ADVISOR` | Soft-delete one client payment |
| `POST` | `/clients/{client_id}/advance-payments/generate` | `require_role(...)` | `ADVISOR` | Generate yearly monthly or bi-monthly schedule |
| `GET` | `/advance-payments/overview` | `require_role(...)` | `ADVISOR`, `SECRETARY` | List cross-client overview rows and KPI totals |

---

## Cross-Domain Dependencies

| Imported From | What | Why |
|---------------|------|-----|
| `app.clients.models.client` | `ClientStatus`, `Client` | Block create for closed/frozen clients; join client name in overview aggregates |
| `app.clients.repositories.client_repository` | `ClientRepository` | Load clients in services and schedule generation |
| `app.vat_reports.repositories.vat_client_summary_repository` | `VatClientSummaryRepository` | Read prior-year output VAT for suggestions |
| `app.annual_reports.services.financial_service` | `AnnualReportFinancialService` | Invalidate annual-report tax calculation after marking a payment as paid |
| `app.users.api.deps` | `CurrentUser`, `DBSession`, `require_role` | API auth and injected DB session |
| `app.users.models.user` | `UserRole` | Endpoint role guards |
| `app.core.api_types` | `ApiDecimal`, `ApiDateTime` | Shared response/request serialization types |

Dependency direction:

- `advance_payments -> clients`
- `advance_payments -> vat_reports`
- `advance_payments -> annual_reports`
- `advance_payments -> users`
- `advance_payments -> core/common`

---

## Tasks

- [ ] **[ARCH]** Move tax invalidation logic out of the router  
  _File_: `app/advance_payments/api/advance_payments.py:138`  
  _Problem_: The router derives the tax year from `period`, calls `AnnualReportFinancialService` directly, and swallows exceptions instead of keeping the HTTP layer thin.  
  _Fix_: Move the decision and cross-domain call into an `advance_payments` service or event hook, and keep the router limited to HTTP coordination.

- [ ] **[ARCH]** Remove cross-domain model import from the repository layer  
  _File_: `app/advance_payments/repositories/advance_payment_aggregation_repository.py:73`  
  _Problem_: The repository imports `Client` from the `clients` domain and joins against it, which breaks the rule against cross-domain dependencies in the model/repository layers.  
  _Fix_: Move client-name enrichment to a service-level aggregation flow or expose it through a `clients` service.

- [ ] **[ARCH]** Replace direct cross-domain repository access with service-to-service boundaries  
  _File_: `app/advance_payments/services/advance_payment_service.py:16`  
  _Problem_: The service depends directly on `ClientRepository` and `VatClientSummaryRepository`, bypassing the service boundaries of `clients` and `vat_reports`.  
  _Fix_: Consume public services from those domains or add a dedicated facade instead of calling their repositories directly.

- [ ] **[ARCH]** Remove direct `ClientRepository` access from schedule generation  
  _File_: `app/advance_payments/services/advance_payment_generator.py:28`  
  _Problem_: The generation flow checks client existence through another domain’s repository instead of going through a service boundary.  
  _Fix_: Move the client validation into a dedicated service or obtain the client through a public `clients` service API.

- [ ] **[PERF]** Eliminate queries inside the annual schedule generation loop  
  _File_: `app/advance_payments/services/advance_payment_generator.py:43`  
  _Problem_: Each month runs `exists_for_period()` and then `create()` with its own `commit`, producing repeated queries and writes inside the loop.  
  _Fix_: Preload the existing periods, compute the missing ones in memory, and insert them in a single transaction.

- [ ] **[CODE]** Split the oversized schema module  
  _File_: `app/advance_payments/schemas/advance_payment.py:1`  
  _Problem_: The file is 163 lines long and exceeds the 150-line threshold used in this domain review.  
  _Fix_: Split the schemas into request/response modules or by use case so each file stays focused and below the threshold.

- [ ] **[CODE]** Split the oversized API router  
  _File_: `app/advance_payments/api/advance_payments.py:1`  
  _Problem_: The file is 161 lines long and combines CRUD, suggestion, KPI, and chart endpoints in one module.  
  _Fix_: Split the router by responsibility, for example CRUD versus analytics, to stay within the size limit and reduce responsibility mixing.

