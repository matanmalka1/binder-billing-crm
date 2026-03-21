# Actions Module

> Last audited: 2026-03-21 (domain-by-domain backend sync).

Defines executable UI action contracts shared across domains (businesses, binders, charges, tax deadlines, annual reports).

## Scope

This module provides:
- Canonical action-contract builder (`build_action`)
- Stable action-id generation convention (`{resource}-{id}-{key}`)
- Domain action factories for binders, businesses, and charges
- Domain action factories for tax deadlines and annual reports
- Role-aware action filtering (for example advisor-only actions)
- Confirm-dialog metadata and optional payload contracts for frontend executors

## Domain Model

This module does not define database tables.

Primary output model is a plain action contract object:
- `id` (stable action ID)
- `key` (action key)
- `label` (Hebrew user label)
- `method` (HTTP method)
- `endpoint` (relative API endpoint)
- `payload` (optional request payload)
- `confirm` (optional confirmation metadata)

Common action producers:
- `get_binder_actions(binder)`
- `get_business_actions(business, user_role=None)`
- `get_charge_actions(charge)`
- `get_tax_deadline_actions(deadline)`
- `get_annual_report_actions(report_id, status)`

Implementation references:
- Contracts: `app/actions/action_contracts.py`
- Tax/annual actions: `app/actions/report_deadline_actions.py`

## API

This module has no FastAPI router and no direct HTTP endpoints.

It is consumed internally by other modules that attach `available_actions` (and in timeline also `actions`) to response payloads.

## Behavior Notes

- `build_action` is the canonical constructor for action dictionaries.
- Action IDs are deterministic via `_generate_action_id(resource, resource_id, key)`.
- Binder actions:
  - `in_office` => `ready`
  - `ready_for_pickup` => `return` (requires `pickup_person_name` input in confirm metadata)
- Business actions:
  - `active` => `freeze` (advisor only; or when role context is absent)
  - `frozen` => `activate`
- Charge actions:
  - `draft` => `issue_charge`, `cancel_charge`
  - `issued` => `mark_paid`, `cancel_charge`
- Tax deadline actions:
  - non-completed deadline => `complete`
  - always includes `edit`
- Annual report actions:
  - `submitted` => `amend`
  - statuses outside final states include `submit`
- Contracts are intentionally transport-oriented (`method` + `endpoint` + optional `payload/confirm`) so frontend can execute actions generically.

## Error Envelope

This module itself does not raise HTTP/domain envelopes because it does not expose routes.

Validation and error envelopes are handled by the endpoint that executes each action target.

## Cross-Domain Integration

- `businesses` APIs attach `available_actions` via `get_business_actions`.
- `binders` list/event services attach binder actions via `get_binder_actions`.
- `charge` and dashboard quick-actions use `get_charge_actions`.
- `tax_deadline` responses attach actions via `get_tax_deadline_actions`.
- `annual_reports` response projection attaches actions via `get_annual_report_actions`.
- `timeline` event builders copy generated actions to both `actions` and `available_actions` for compatibility.

## Tests

No dedicated actions-only test package currently exists.

Actions behavior is covered indirectly by domain tests, including:
- `tests/businesses/api/test_businesses.py`
- `tests/binders/api/test_binders.py`
- `tests/timeline/service/test_timeline_event_builders.py`
- `tests/timeline/service/test_timeline_event_builders_additional.py`
- `tests/timeline/service/test_timeline_tax_builders.py`

Run related suites:

```bash
pytest tests/businesses tests/binders tests/timeline -q
```