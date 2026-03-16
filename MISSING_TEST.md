# Missing Tests Report

Updated on March 16, 2026.

Audit basis:
- Full backend run: `coverage run --source=app -m pytest -q`
- Result: `400 passed, 1 failed, 1 skipped`, total coverage `89%`
- This file lists **remaining** missing tests only.

## 1) Immediate Regression To Fix

- `tests/annual_reports/api/test_annual_report_financials.py::test_tax_calculation_includes_pension_and_donations`
  - Expected `credit_points_value` no longer matches current engine behavior.
  - Add/adjust tests to lock current business rule for credit-point valuation.

## 2) High-Priority Missing Tests (Core Business Flows)

### `reports` domain

- `app/reports/services/vat_compliance_report.py` (25%)
  - Add service tests for compliance aggregation, year/period grouping, edge statuses.
- `app/reports/services/annual_report_status_report.py` (32%)
  - Add tests for per-status totals, year filters, and ordering.
- `app/reports/services/advance_payment_report.py` (42%)
  - Add tests for overdue/paid buckets, totals, and month filtering.
- `app/reports/api/reports.py` (70%)
  - Add API tests for `/reports/advance-payments`, `/reports/annual-reports`, and invalid format handling in `/reports/aging/export`.

### `tax_deadline` domain

- `app/tax_deadline/services/deadline_generator.py` (30%)
  - Add idempotency tests (duplicate generation prevention).
  - Add rule tests for each generated deadline type and due-date windows.
- `app/tax_deadline/api/deadline_generate.py` (73%)
  - Add endpoint tests for generation success and error paths.

### `reminders` domain

- `app/reminders/services/factory.py` (69%)
  - Add tests for all trigger combinations and dedup behavior.
- `app/reminders/api/routes_create.py` (67%)
  - Add API validation/error tests and role enforcement assertions.

### `clients` domain

- `app/clients/services/client_service.py` (59%)
  - Add service tests for update/delete/not-found edge cases and pagination behavior.
- `app/clients/api/clients.py` (61%)
  - Add endpoint tests for invalid query params, pagination boundaries, and error mapping.

## 3) Medium-Priority Missing Tests (Important Internals)

### `annual_reports`

- `app/annual_reports/services/status_service.py` (66%)
  - Add tests for disallowed transitions across all states and submitted/readiness guards.
- `app/annual_reports/services/financial_crud_service.py` (56%)
  - Add tests for update/delete not-found branches and validation failures.
- `app/annual_reports/repositories/income_repository.py` (59%)
- `app/annual_reports/repositories/expense_repository.py` (63%)
  - Add repository tests for filters, ordering, and null/empty totals.

### `signature_requests`

- `app/signature_requests/services/signer_actions.py` (66%)
  - Add tests for token invalid/expired flows, re-sign prevention, and decline edge cases.

### `binders`

- `app/binders/api/binders_list_get.py` (62%)
  - Add API tests for list filtering/sorting combinations and pagination limits.
- `app/binders/services/binder_list_service.py` (80%)
  - Add tests for all signal filters with mixed datasets.

## 4) Lower-Priority Infrastructure / Utility Gaps

- `app/infrastructure/notifications.py` (53%)
  - Add adapter tests with channel failure/success permutations.
- `app/infrastructure/storage.py` (57%)
  - Add provider selection tests and upload/download error paths.
- `app/core/background_jobs.py` (51%)
  - Add idempotency and retry-safety tests for scheduled jobs.
- `app/utils/excel.py` (62%)
  - Add tests for column auto-width and temp-file failure handling.

## 5) Suggested Execution Order

1. Fix annual-report tax regression test and align expected engine behavior.
2. Add missing `reports/*` service+API tests.
3. Add `tax_deadline` generator idempotency and API tests.
4. Expand `clients` and `reminders` uncovered branches.
5. Backfill infra/utils coverage.

## 6) Goal

- Short term: raise backend coverage from `89%` to `>=92%`.
- Targeted threshold for core business domains (`annual_reports`, `tax_deadline`, `reports`, `clients`): `>=95%`.
