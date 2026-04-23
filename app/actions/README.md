# Actions Module

> Last audited: 2026-04-23

Defines executable UI action contracts shared across domains (businesses, binders, charges, tax deadlines, annual reports).
Also owns cross-domain application workflows that do not belong to a single domain.

## Scope

This module provides:
- Canonical action-contract builder (`build_action`)
- Canonical confirm builder (`build_confirm`)
- Stable action-id generation convention (`{resource}-{id}-{key}`)
- Domain action factories for binders, businesses, charges, tax deadlines, and annual reports
- Role-aware action filtering (for example advisor-only actions)
- Confirm-dialog metadata and optional payload contracts for frontend executors
- `obligation_orchestrator.py` — cross-domain workflow that generates tax deadlines and annual reports for a client (idempotent; used on client create/update and business create)
- `ObligationResult` / `generate_client_obligations_result(...)` — explicit partial-success breakdown for obligation generation

## Domain Model

This module does not define database tables.

Primary output model is a typed action contract (`ActionContract` via `TypedDict`):
- `id` (stable action ID)
- `key` (action key)
- `label` (Hebrew user label)
- `method` (validated HTTP method: `get|post|put|patch|delete`)
- `endpoint` (relative API endpoint)
- `payload` (optional request payload)
- `confirm` (optional confirmation metadata)

Confirm metadata is also typed (`ActionConfirm`) and currently supports:
- `title`
- `message`
- `confirm_label`
- `cancel_label`
- `inputs` (optional; currently validated for supported input types only)

Common action producers:
- `get_binder_actions(binder)`
- `get_business_actions(business, user_role=None)`
- `get_charge_actions(charge)`
- `get_tax_deadline_actions(deadline)`
- `get_annual_report_actions(report_id, status)`
- `generate_client_obligations_result(...)`

Implementation references:
- Contracts: `app/actions/action_contracts.py`
- Shared helpers: `app/actions/action_helpers.py`
- Binder actions: `app/actions/binder_actions.py`
- Business actions: `app/actions/business_actions.py`
- Charge actions: `app/actions/charge_actions.py`
- Tax/annual actions: `app/actions/report_deadline_actions.py`
- Obligation workflow: `app/actions/obligation_orchestrator.py`

## API

This module has no FastAPI router and no direct HTTP endpoints.

It is consumed internally by other modules that attach `available_actions` (and in timeline also `actions`) to response payloads.

## Behavior Notes

- `build_action` is the canonical constructor for action contracts and validates supported HTTP methods.
- `build_confirm` is the canonical constructor for confirm dialogs and centralizes common confirm metadata.
- Action IDs are deterministic via `_generate_action_id(resource, resource_id, key)`.
- Binder actions:
  - `in_office` => `ready`
  - `ready_for_pickup` => `return` (requires `pickup_person_name` input in confirm metadata)
- Business actions:
  - endpoints are built only from `client_id`; missing `client_id` fails fast
  - `active` => `freeze` (advisor only)
  - `frozen` => `activate`
- Charge actions:
  - `draft` => `issue_charge`, `cancel_charge`
  - `issued` => `mark_paid`, `cancel_charge`
- Tax deadline actions:
  - `pending` => `complete`, `edit`, `delete`
  - `delete` requires confirm metadata
  - `completed` => `reopen` only
  - `canceled` => no actions
- Annual report actions:
  - `submitted` => `amend`
  - statuses outside final states include `submit`
- Contracts are intentionally transport-oriented (`method` + `endpoint` + optional `payload/confirm`) so frontend can execute actions generically.
- `obligation_orchestrator.py` fails fast on unsupported `entity_type`; it does not default annual reports to `INDIVIDUAL`.
- `generate_client_obligations(...)` preserves the legacy `int` return API for existing callers.
- `generate_client_obligations_result(..., best_effort=True)` exposes the intentional partial-success design explicitly via:
  - `deadlines_created`
  - `reports_created`
  - `errors`
- `_generate_action_id` and `_value` remain internal helpers from `action_helpers.py`; `action_contracts.py` no longer re-exports them as public API.

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

Actions behavior is covered by direct and domain tests, including:
- `tests/actions/test_action_contracts.py`
- `tests/actions/test_business_actions.py`
- `tests/actions/test_obligation_orchestrator.py`
- `tests/actions/test_report_deadline_actions.py`
- `tests/actions/test_binder_actions.py`
- `tests/businesses/api/test_businesses.py`
- `tests/binders/api/test_binders.py`
- `tests/timeline/service/test_timeline_event_builders.py`
- `tests/timeline/service/test_timeline_event_builders_additional.py`
- `tests/timeline/service/test_timeline_tax_builders.py`

Run related suites:

```bash
JWT_SECRET=test-secret pytest -q tests/actions tests/businesses tests/binders tests/timeline
```
