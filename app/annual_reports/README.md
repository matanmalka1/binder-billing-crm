# Annual Reports Module

> Last audited: 2026-04-11

Manages annual income-tax report lifecycle per client: creation, workflow statuses, schedules/annex lines, financial lines, tax/readiness calculation, season summary, and PDF export.

## Scope

This module provides:
- Annual report CRUD (create/list/get/soft-delete)
- Status transitions, submit/amend, deadline update, and status history
- Stage transition for Kanban workflows
- Schedules (required annex tracking)
- Annex data lines per schedule
- Detail section (deductions/approval/internal notes)
- Income/expense line CRUD, financial summary, readiness, tax calculation, and advances summary
- Client-level and tax-year-level listing/summary endpoints
- Working-draft PDF export

## Domain Model

Primary entity: `AnnualReport` (`app/annual_reports/models/annual_report_model.py`)
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
- `submission_method`, `extension_reason` (optional)
- `notes` (optional)
- `created_at`, `updated_at`
- `deleted_at`, `deleted_by` (soft delete)

Active-record uniqueness:
- one non-deleted annual report per (`client_id`, `tax_year`) via partial unique index

Related entities:
- `AnnualReportDetail`
- `AnnualReportIncomeLine`
- `AnnualReportExpenseLine`
- `AnnualReportScheduleEntry`
- `AnnualReportAnnexData`
- `AnnualReportStatusHistory`

## Enums

From `app/annual_reports/models/annual_report_enums.py`.

`AnnualReportStatus`:
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

`AnnualReportSchedule`:
- `schedule_b`
- `schedule_bet`
- `schedule_gimmel`
- `schedule_dalet`
- `schedule_heh`
- `schedule_a`
- `schedule_vav`
- `annex_15`
- `annex_867`

`DeadlineType`:
- `standard`
- `extended`
- `custom`

`ClientTypeForReport`:
- `individual`
- `self_employed`
- `corporation`
- `partnership`

## API

Routers are mounted in `app/router_registry.py` with `/api/v1` prefix.

### Core (`/api/v1/annual-reports`)

- `POST /annual-reports` (ADVISOR, SECRETARY)
- `GET /annual-reports` (ADVISOR, SECRETARY)
- `GET /annual-reports/kanban/view` (ADVISOR, SECRETARY)
- `GET /annual-reports/overdue` (ADVISOR, SECRETARY)
- `GET /annual-reports/{report_id}` (ADVISOR, SECRETARY)
- `DELETE /annual-reports/{report_id}` (ADVISOR only)
- `POST /annual-reports/{report_id}/amend` (ADVISOR only)
- `GET /annual-reports/{report_id}/export/pdf` (ADVISOR, SECRETARY)

### Status & workflow (`/api/v1/annual-reports`)

- `POST /{report_id}/status` (ADVISOR only)
- `POST /{report_id}/submit` (ADVISOR only)
- `POST /{report_id}/deadline` (ADVISOR only)
- `GET /{report_id}/history` (ADVISOR, SECRETARY)
- `POST /{report_id}/transition` (ADVISOR only)

### Detail (`/api/v1/annual-reports`)

- `GET /{report_id}/details` (ADVISOR, SECRETARY)
- `PATCH /{report_id}/details` (ADVISOR, SECRETARY)

### Financial (`/api/v1/annual-reports`)

- `GET /{report_id}/financials` (ADVISOR, SECRETARY)
- `GET /{report_id}/tax-calculation` (ADVISOR, SECRETARY)
- `GET /{report_id}/advances-summary` (ADVISOR, SECRETARY)
- `GET /{report_id}/readiness` (ADVISOR, SECRETARY)
- `POST /{report_id}/income` (ADVISOR, SECRETARY)
- `PATCH /{report_id}/income/{line_id}` (ADVISOR only)
- `DELETE /{report_id}/income/{line_id}` (ADVISOR only)
- `POST /{report_id}/expenses` (ADVISOR, SECRETARY)
- `PATCH /{report_id}/expenses/{line_id}` (ADVISOR only)
- `DELETE /{report_id}/expenses/{line_id}` (ADVISOR only)

### Schedules & annex (`/api/v1/annual-reports`)

- `POST /{report_id}/schedules` (ADVISOR only)
- `GET /{report_id}/schedules` (ADVISOR, SECRETARY)
- `POST /{report_id}/schedules/complete` (ADVISOR only)
- `GET /{report_id}/annex/{schedule}` (ADVISOR, SECRETARY)
- `POST /{report_id}/annex/{schedule}` (ADVISOR, SECRETARY)
- `PATCH /{report_id}/annex/{schedule}/{line_id}` (ADVISOR, SECRETARY)
- `DELETE /{report_id}/annex/{schedule}/{line_id}` (ADVISOR only)

### Cross-prefix views

- `GET /api/v1/clients/{client_id}/annual-reports` (ADVISOR, SECRETARY)
- `GET /api/v1/tax-year/{tax_year}/reports` (ADVISOR, SECRETARY)
- `GET /api/v1/tax-year/{tax_year}/summary` (ADVISOR, SECRETARY)

## Request/Behavior Notes

- Create payload uses `client_id`.
- On create:
  - validates client existence and client-create guards
  - validates `assigned_to` user when provided
  - maps `client_type -> form_type`
  - computes deadline for `standard`/`extended`; keeps `filing_deadline=None` for `custom`
  - auto-generates required schedules from report flags:
    - `has_rental_income -> schedule_b`
    - `has_capital_gains -> schedule_bet`
    - `has_foreign_income -> schedule_gimmel`
    - `has_depreciation -> schedule_dalet`
    - `has_exempt_rental -> schedule_heh`
  - appends initial status history entry (`not_started`)
- Status transitions are constrained by `VALID_TRANSITIONS` in `services/constants.py`.
- Transition to `submitted` enforces readiness check (`schedules complete`, `income entered`, `tax due/refund present`, `client approved`).
- Entering `pending_client` triggers a signature request; leaving it cancels pending signature requests.
- `amend` is allowed only from `submitted` and stores amendment reason.
- Delete is soft-delete and cancels pending signature requests.
- Overdue endpoint supports `tax_year`, `page`, `page_size`; returns open reports past `filing_deadline`.

## Known Gaps (Current Implementation)

These are observable from current code and should be treated as implementation caveats:
- `AnnualReportCreateRequest` includes `submission_method` and `extension_reason`, but `create_report(...)` currently does not persist them.
- `SubmitRequest` includes `submission_method`, but submit flow currently ignores it.
- Annex `schedule` path param is used for routing/validation, but update/delete operations currently resolve by `line_id` only after report existence check.

## Errors

Uses global app exception envelope (`app/core/exceptions.py`) with fields like:
- `detail`
- `error`
- `error_meta`

Common domain error codes:
- `ANNUAL_REPORT.NOT_FOUND`
- `ANNUAL_REPORT.CONFLICT`
- `ANNUAL_REPORT.INVALID_STATUS`
- `ANNUAL_REPORT.INVALID_TYPE`
- `ANNUAL_REPORT.INVALID_STAGE`
- `ANNUAL_REPORT.LINE_NOT_FOUND`
- `ANNUAL_REPORT.INVALID_STATUS_FOR_AMEND`

## Cross-Domain Integrations

- `clients`: existence/guards and client-level report listing
- `users`: RBAC and actor attribution
- `signature_requests`: auto-create/cancel around `pending_client` workflow
- `advance_payments`: advances summary/final balance
- `vat_reports`: VAT balance included in tax liability
- `permanent_documents`: expense lines may reference supporting documents
- `actions`: dynamic `available_actions` on report responses

## Tests

Use these test suites as the source of truth for behavior:
- `tests/annual_reports/api/`
- `tests/annual_reports/repository/`
- `tests/annual_reports/service/`

Run all annual-report tests:

```bash
pytest tests/annual_reports -q
```
