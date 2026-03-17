# Dashboard Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages dashboard widgets and operational summaries (overview metrics, work queue, attention items, and tax submission statistics) used by the CRM home/dashboard screens.

## Scope

This module provides:
- Dashboard summary counters
- Management overview metrics + quick actions
- Operational work queue
- Attention items feed
- Tax submission widget for annual reports
- Role-based API access per widget

## Domain Model

Dashboard does not define persistent domain tables.

It composes data from other domains and returns derived response models:
- `DashboardSummaryResponse`
- `DashboardOverviewResponse`
- `WorkQueueResponse`
- `AttentionResponse`
- `TaxSubmissionWidgetResponse`

Implementation references:
- APIs: `app/dashboard/api/dashboard.py`, `app/dashboard/api/dashboard_overview.py`, `app/dashboard/api/dashboard_extended.py`, `app/dashboard/api/dashboard_tax.py`
- Schemas: `app/dashboard/schemas/dashboard.py`, `app/dashboard/schemas/dashboard_extended.py`, `app/dashboard/schemas/dashboard_tax.py`
- Services: `app/dashboard/services/dashboard_service.py`, `app/dashboard/services/dashboard_overview_service.py`, `app/dashboard/services/dashboard_extended_service.py`, `app/dashboard/services/dashboard_tax_service.py`
- Dashboard-specific helpers/builders: `app/dashboard/services/dashboard_extended_builders.py`, `app/dashboard/services/dashboard_quick_actions_builder.py`

## API

Router prefix is `/api/v1/dashboard` (mounted in `app/main.py`).

### Summary
- `GET /api/v1/dashboard/summary`
- Roles: authenticated user (via `CurrentUser`)
- Returns:
  - `binders_in_office`
  - `binders_ready_for_pickup`
  - `attention` (`items`, `total`)

### Overview
- `GET /api/v1/dashboard/overview`
- Role: `ADVISOR` only
- Returns management-level overview:
  - `total_clients`
  - `active_binders`
  - `quick_actions`
  - `attention`

### Work queue
- `GET /api/v1/dashboard/work-queue`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)
- Returns operational binder queue with:
  - `binder_id`, `client_id`, `client_name`
  - `binder_number`, `work_state`, `signals`
  - `days_since_received`

### Attention
- `GET /api/v1/dashboard/attention`
- Roles: `ADVISOR`, `SECRETARY`
- Returns attention items requiring action/review.

### Tax submissions widget
- `GET /api/v1/dashboard/tax-submissions`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `tax_year` (optional, `>= 1900`; default = current year)
- Returns:
  - `tax_year`, `total_clients`
  - `reports_submitted`, `reports_in_progress`, `reports_not_started`
  - `submission_percentage`
  - `total_refund_due`, `total_tax_due`

## Behavior Notes

- Summary counters are based on binder statuses (`IN_OFFICE`, `READY_FOR_PICKUP`) and include attention feed.
- Overview combines repository metrics with cross-domain quick actions and attention items.
- Dashboard domain does not define its own repository package; services compose repositories from other domains (`clients`, `binders`, `charge`, `annual_reports`, `vat_reports`, `reminders`).
- Work queue and attention are computed from active binders and derived signals/work-state.
- Advisor-only attention enrichment includes unpaid issued charges.
- Tax-submission widget derives progress buckets from annual-report statuses and active client count.
- `DashboardExtendedService` has hard in-memory safety limits:
  - Active binders fetch ceiling: `1000`
  - Unpaid charges fetch ceiling: `500`
  - Exceeding limits raises `DASHBOARD.LIMIT_EXCEEDED`.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `DASHBOARD.LIMIT_EXCEEDED`

## Cross-Domain Integration

Dashboard aggregates across:
- `binders` (status counts, active binders, work-state, signals, binder actions)
- `clients` (counts, names, client actions)
- `charge` (issued/unpaid charges, charge actions)
- `annual_reports` (tax-submission widget metrics and financial sums)
- `actions` (`app/actions/action_contracts.py` for quick actions)

## Tests

Dashboard test suites:
- `tests/dashboard/api/test_dashboard_extended.py`
- `tests/dashboard/api/test_dashboard_tax.py`
- `tests/dashboard/service/test_dashboard_service.py`
- `tests/dashboard/service/test_dashboard_extended_service.py`
- `tests/dashboard/service/test_dashboard_overview_service.py`
- `tests/dashboard/service/test_dashboard_extended_builders.py`
- `tests/dashboard/repository/test_dashboard_overview_repository.py`

Run only this domain:

```bash
pytest tests/dashboard -q
```
