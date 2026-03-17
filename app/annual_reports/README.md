# Annual Reports Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages annual income-tax report lifecycle for clients, including creation, status workflow, schedules/annexes, financial lines, tax calculations, and season dashboards.

## Scope

This module provides:
- Annual report creation, listing, retrieval, and soft delete
- Status transitions, submit/amend actions, and status history
- Deadline-type updates (standard/extended/custom)
- Schedule management and annex data lines
- Report detail section (credits, approvals, internal notes)
- Income/expense line CRUD, financial summary, readiness check, tax calculation
- Working-draft PDF export for annual reports
- Client-level and tax-year (season) reporting views
- Kanban view and overdue reports

## Domain Model

`AnnualReport` fields:
- `id` (PK)
- `client_id` (FK, required)
- `created_by` (FK, required)
- `assigned_to` (FK, optional)
- `tax_year` (required)
- `client_type` (enum)
- `form_type` (enum)
- `status` (enum)
- `deadline_type` (enum)
- `filing_deadline` (optional)
- `custom_deadline_note` (optional)
- `submitted_at` (optional)
- `ita_reference` (optional)
- `assessment_amount`, `refund_due`, `tax_due` (optional)
- Schedule flags: `has_rental_income`, `has_capital_gains`, `has_foreign_income`, `has_depreciation`, `has_exempt_rental`
- `notes` (optional)
- `created_at`, `updated_at`
- `deleted_at`, `deleted_by` (soft delete)

Uniqueness:
- one annual report per (`client_id`, `tax_year`)

Related entities:
- `AnnualReportDetail` (credit points, pension/donation credits, approval, notes, amendment reason)
- `AnnualReportIncomeLine`
- `AnnualReportExpenseLine`
- `AnnualReportScheduleEntry`
- `AnnualReportAnnexData`
- `AnnualReportStatusHistory`

Status enum values:
- `not_started`
- `collecting_docs`
- `docs_complete`
- `in_preparation`
- `pending_client`
- `submitted`
- `amended`
- `accepted`
- `assessment_issued`
- `objection_filed`
- `closed`

Schedule enum values:
- `schedule_b`
- `schedule_bet`
- `schedule_gimmel`
- `schedule_dalet`
- `schedule_heh`

Deadline type enum values:
- `standard`
- `extended`
- `custom`

Implementation references:
- Models: `app/annual_reports/models/`
- Schemas: `app/annual_reports/schemas/`
- Repositories: `app/annual_reports/repositories/`
- Services: `app/annual_reports/services/`
- API: `app/annual_reports/api/`

## API

Routers are mounted in `app/main.py` under `/api/v1`.

### Core report endpoints (`/api/v1/annual-reports`)

#### Create annual report
- `POST /api/v1/annual-reports`
- Roles: `ADVISOR`, `SECRETARY`
- Body:

```json
{
  "client_id": 123,
  "tax_year": 2025,
  "client_type": "self_employed",
  "deadline_type": "standard",
  "assigned_to": 45,
  "notes": "Initial draft",
  "has_rental_income": false,
  "has_capital_gains": false,
  "has_foreign_income": false,
  "has_depreciation": true,
  "has_exempt_rental": false
}
```

#### List annual reports
- `GET /api/v1/annual-reports`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `tax_year` (optional)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `200`)
  - `sort_by` (`tax_year|status|filing_deadline|created_at|client_id`)
  - `order` (`asc|desc`)

#### Kanban view
- `GET /api/v1/annual-reports/kanban/view`
- Roles: `ADVISOR`, `SECRETARY`

#### Overdue reports
- `GET /api/v1/annual-reports/overdue`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `tax_year` (optional)

#### Get report
- `GET /api/v1/annual-reports/{report_id}`
- Roles: `ADVISOR`, `SECRETARY`

#### Delete report (soft delete)
- `DELETE /api/v1/annual-reports/{report_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

#### Amend report
- `POST /api/v1/annual-reports/{report_id}/amend`
- Role: `ADVISOR` only

#### Export PDF (working draft)
- `GET /api/v1/annual-reports/{report_id}/export/pdf`
- Roles: `ADVISOR`, `SECRETARY`
- Returns `application/pdf` stream with attachment filename:
  - `annual_report_{report_id}_{tax_year}.pdf`

### Status/deadline/history endpoints

#### Transition status
- `POST /api/v1/annual-reports/{report_id}/status`
- Roles: `ADVISOR`, `SECRETARY`

#### Submit report
- `POST /api/v1/annual-reports/{report_id}/submit`
- Roles: `ADVISOR`, `SECRETARY`

#### Update deadline type
- `POST /api/v1/annual-reports/{report_id}/deadline`
- Roles: `ADVISOR`, `SECRETARY`

#### Status history
- `GET /api/v1/annual-reports/{report_id}/history`
- Roles: `ADVISOR`, `SECRETARY`

#### Stage transition
- `POST /api/v1/annual-reports/{report_id}/transition`
- Roles: `ADVISOR`, `SECRETARY`

### Details endpoint

#### Get/update details
- `GET /api/v1/annual-reports/{report_id}/details`
- `PATCH /api/v1/annual-reports/{report_id}/details`
- Roles: `ADVISOR`, `SECRETARY`

### Financial endpoints

#### Summary/tax/readiness/advances
- `GET /api/v1/annual-reports/{report_id}/financials`
- `GET /api/v1/annual-reports/{report_id}/tax-calculation`
- `GET /api/v1/annual-reports/{report_id}/readiness`
- `GET /api/v1/annual-reports/{report_id}/advances-summary`
- Roles: `ADVISOR`, `SECRETARY`

#### Income lines
- `POST /api/v1/annual-reports/{report_id}/income`
- `PATCH /api/v1/annual-reports/{report_id}/income/{line_id}`
- `DELETE /api/v1/annual-reports/{report_id}/income/{line_id}` (`ADVISOR` only)

#### Expense lines
- `POST /api/v1/annual-reports/{report_id}/expenses`
- `PATCH /api/v1/annual-reports/{report_id}/expenses/{line_id}`
- `DELETE /api/v1/annual-reports/{report_id}/expenses/{line_id}` (`ADVISOR` only)

### Schedules and annex endpoints

#### Schedules
- `POST /api/v1/annual-reports/{report_id}/schedules`
- `GET /api/v1/annual-reports/{report_id}/schedules`
- `POST /api/v1/annual-reports/{report_id}/schedules/complete`
- Roles: `ADVISOR`, `SECRETARY`

#### Annex lines
- `GET /api/v1/annual-reports/{report_id}/annex/{schedule}`
- `POST /api/v1/annual-reports/{report_id}/annex/{schedule}`
- `PATCH /api/v1/annual-reports/{report_id}/annex/{schedule}/{line_id}`
- `DELETE /api/v1/annual-reports/{report_id}/annex/{schedule}/{line_id}` (`ADVISOR` only)

### Cross-prefix listing endpoints

#### Client reports
- `GET /api/v1/clients/{client_id}/annual-reports`
- Roles: `ADVISOR`, `SECRETARY`

#### Tax-year reports and summary
- `GET /api/v1/tax-year/{tax_year}/reports`
- `GET /api/v1/tax-year/{tax_year}/summary`
- Roles: `ADVISOR`, `SECRETARY`

## Behavior Notes

- `client_type` determines `form_type` at creation (via service mapping).
- Duplicate report creation for same (`client_id`, `tax_year`) is rejected.
- Required schedules are auto-generated at creation from schedule flags.
- Status changes are validated against allowed transitions.
- Submitting (`submitted`) enforces readiness checks before transition.
- Deadline updates recompute filing deadline for `standard`/`extended`; `custom` uses note/manual handling.
- Report delete is soft-delete (`deleted_at`, `deleted_by`).
- Tax calculation uses income/expenses + detail credits, and includes NI and VAT/advance-payment integration.
- PDF export produces a Hebrew working draft (`טיוטה לעיון`) built from report metadata, financial summary, tax calculation, and detail data.
- Annex and line-level endpoints return not-found for missing report/line resources.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `ANNUAL_REPORT.NOT_FOUND`
- `ANNUAL_REPORT.CONFLICT`
- `ANNUAL_REPORT.INVALID_STATUS`
- `ANNUAL_REPORT.INVALID_TYPE`
- `ANNUAL_REPORT.INVALID_STAGE`
- `ANNUAL_REPORT.LINE_NOT_FOUND`
- `ANNUAL_REPORT.INVALID_STATUS_FOR_AMEND`

Additional route-specific HTTP errors are also used for authorization and validation failures.

## Cross-Domain Integration

- `clients`: validates client existence and exposes `/clients/{client_id}/annual-reports`.
- `users`: role-based access control and actor metadata for status/history.
- `advance_payments`: tax/advances summary and final balance calculations.
- `vat_reports`: VAT totals are included in tax liability calculations.
- `permanent_documents`: expense lines may link supporting documents.

## Tests

Annual reports test suites:
- `tests/annual_reports/api/test_annual_report_advances_summary.py`
- `tests/annual_reports/api/test_annual_report_annex.py`
- `tests/annual_reports/api/test_annual_report_client_and_season_list.py`
- `tests/annual_reports/api/test_annual_report_detail.py`
- `tests/annual_reports/api/test_annual_report_financials.py`
- `tests/annual_reports/api/test_annual_report_fixes.py`
- `tests/annual_reports/api/test_annual_report_overdue_amend_and_summary.py`
- `tests/annual_reports/api/test_annual_report_readiness.py`
- `tests/annual_reports/api/test_annual_report_schedule.py`
- `tests/annual_reports/api/test_annual_report_status.py`
- `tests/annual_reports/repository/test_annual_report_domain_repositories.py`
- `tests/annual_reports/repository/test_annual_report_report_repository.py`
- `tests/annual_reports/service/test_annual_report.py`
- `tests/annual_reports/service/test_annual_report_delete_report.py`
- `tests/annual_reports/service/test_annual_report_enums.py`
- `tests/annual_reports/service/test_annual_report_forms_deadlines.py`
- `tests/annual_reports/service/test_annual_report_query_service.py`
- `tests/annual_reports/service/test_annual_report_readiness.py`
- `tests/annual_reports/service/test_annual_report_repo.py`
- `tests/annual_reports/service/test_annual_report_schedules.py`
- `tests/annual_reports/service/test_annual_report_status_history.py`
- `tests/annual_reports/service/test_annual_report_summary_overdue.py`
- `tests/annual_reports/service/test_tax_engine.py`

Run only this domain:

```bash
pytest tests/annual_reports -q
```
