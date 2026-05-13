# Dashboard Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages dashboard widgets and operational summaries (overview metrics, attention items, and tax submission statistics) used by the CRM home/dashboard screens.

## Scope

This module provides:
- Management overview metrics + quick actions
- Attention items embedded in the overview
- Tax submission widget for annual reports
- Role-based API access per widget

## Domain Model

Dashboard does not define persistent domain tables.

It composes data from other domains and returns derived response models:
- `DashboardOverviewResponse`
- `AttentionResponse`
- `AttentionItem`
- `DashboardQuickAction`
- `TaxSubmissionWidgetResponse`

Implementation references:
- APIs: `app/dashboard/api/dashboard_overview.py`, `app/dashboard/api/dashboard_tax.py`
- Schemas: `app/dashboard/schemas/dashboard_extended.py`, `app/dashboard/schemas/dashboard_tax.py`
- Services: `app/dashboard/services/dashboard_overview_service.py`, `app/dashboard/services/dashboard_extended_service.py`, `app/dashboard/services/dashboard_tax_service.py`
- Dashboard-specific helpers/builders: `app/dashboard/services/dashboard_extended_builders.py`, `app/dashboard/services/dashboard_quick_actions_builder.py`

## API

Router prefix is `/api/v1/dashboard` (mounted through `app/router_registry.py`).

### Overview
- `GET /api/v1/dashboard/overview`
- Roles: `ADVISOR`, `SECRETARY`
- Returns management-level overview:
  - `is_empty`
  - `open_charges_count`
  - `open_charges_amount_ils`
  - `vat_stats` (`monthly`, `bimonthly`, `advance_payments`)
  - `quick_actions`
  - `attention`

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

- Overview combines repository metrics with cross-domain quick actions and attention items.
- Quick actions are advisor-only operational shortcuts for overdue binders, VAT work items, and stuck annual reports. Financial state mutations are intentionally kept out of quick actions.
- Dashboard stat card links deep-link to their matching filtered list views:
  - binders in office: `/binders?status=in_office`
  - monthly/bimonthly VAT: `/tax/vat?period=YYYY-MM&period_type=...`
- Dashboard domain does not define its own repository package; services compose repositories from other domains (`clients`, `binders`, `charge`, `annual_reports`, `vat_reports`).
- Advisor-only attention includes unpaid issued charges.
- The attention payload uses typed items whose `item_type` is currently `charge`.
- Tax-submission widget derives progress buckets from annual-report statuses and active client count.
- `DashboardExtendedService` has hard in-memory safety limits:
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
- `binders` (status counts, active binders, binder actions)
- `clients` (counts, names, client actions)
- `charge` (issued/unpaid charge attention items)
- `annual_reports` (tax-submission widget metrics and financial sums)
- `vat_reports` (VAT due counters and quick actions)
- `actions` (`app/actions/action_contracts.py` for quick actions)

## Tests

Dashboard test suites:
- `tests/dashboard/api/test_dashboard_extended.py`
- `tests/dashboard/api/test_dashboard_tax.py`
- `tests/dashboard/service/test_dashboard_extended_service.py`
- `tests/dashboard/service/test_dashboard_overview_service.py`
- `tests/dashboard/service/test_dashboard_tax_service.py`
- `tests/dashboard/service/test_dashboard_extended_builders.py`
- `tests/dashboard/service/test_dashboard_quick_actions_builder_additional.py`

Run only this domain:

```bash
JWT_SECRET=test-secret pytest -q tests/dashboard
```
