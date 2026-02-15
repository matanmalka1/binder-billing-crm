# UI State Mapping (Backend-Derived Fields → UI Meaning)

Backend fields are authoritative. UI renders states directly from backend fields. UI does not recompute derived states.

## Work State (`work_state`)

Source endpoints:

- `GET /api/v1/dashboard/work-queue` → `items[].work_state`
- `GET /api/v1/search` → `results[].work_state` (binder results)
- `GET /api/v1/binders/open|overdue|due-today` → `items[].work_state`
- `GET /api/v1/clients/{client_id}/binders` → `items[].work_state`

Values and meaning:

- `waiting_for_work`
  - UI label: “Waiting for work”
  - UI emphasis: informational/neutral
- `in_progress`
  - UI label: “In progress”
  - UI emphasis: active
- `completed`
  - UI label: “Completed”
  - UI emphasis: archived/completed

## Binder SLA and Overdue UI

There is no single `sla_state` field returned by the API.

Backend exposes SLA-related UI state via:

- `GET /api/v1/dashboard/alerts`:
  - `items[].alert_type`:
    - `overdue` → overdue alert
    - `near_sla` → approaching SLA alert
  - `items[].days_overdue` / `items[].days_remaining`
- Operational binder lists (`/binders/open|overdue|due-today`, `/clients/{id}/binders`):
  - `items[].is_overdue` (boolean)
  - `items[].days_overdue` (int)
- Binder signals:
  - `signals[]` contains `overdue` or `near_sla` when applicable
- Client operational signals (`GET /api/v1/documents/client/{client_id}/signals`):
  - `binders_overdue[]` and `binders_nearing_sla[]` include binder id/number and day counters

UI rules:

- If `alert_type == "overdue"`, render overdue severity using `days_overdue`.
- If `alert_type == "near_sla"`, render approaching severity using `days_remaining`.
- If `is_overdue == true`, render overdue severity using `days_overdue`.
- If `signals` contains `overdue`, render overdue badge/indicator.
- If `signals` contains `near_sla`, render approaching badge/indicator.

UI does not compute SLA from dates.

## Signals (`signals`)

Source endpoints:

- `GET /api/v1/dashboard/work-queue` → `items[].signals`
- `GET /api/v1/search` → `results[].signals` (binder results)
- Operational binder lists (`/binders/open|overdue|due-today`, `/clients/{id}/binders`) → `items[].signals`

Signal values produced by binder signal computation:

- `overdue`
  - UI meaning: binder is overdue
- `near_sla`
  - UI meaning: binder is in the approaching-SLA window
- `ready_for_pickup`
  - UI meaning: binder status is ready for pickup
- `idle_binder`
  - UI meaning: binder is idle (derived work state is `waiting_for_work`)

UI renders signals as badges/indicators and does not add derived signals.

## Attention Items (`/dashboard/attention`)

Source endpoint:

- `GET /api/v1/dashboard/attention` → `items[]`

`item_type` values and UI actions:

- `idle_binder`
  - UI: open binder details / work queue focus
- `ready_for_pickup`
  - UI: open binder details / pickup workflow
- `unpaid_charge`
  - UI: open billing/charges view for the client

`unpaid_charge` items are returned only for `advisor`.

## Search Result Types (`/search`)

Source endpoint:

- `GET /api/v1/search` → `results[]`

`result_type` values:

- `client`
  - `binder_id` is `null`
  - `signals` is `[]`
- `binder`
  - `binder_id` is set
  - `work_state` is set
  - `signals` is set (binder signals)

## Timeline (`/clients/{id}/timeline`)

Source endpoint:

- `GET /api/v1/clients/{client_id}/timeline` → `events[]`

UI rules:

- Timeline order is already sorted by backend descending timestamp.
- Render by `event_type`:
  - `binder_received`
  - `binder_returned`
  - `binder_status_change`
  - `notification_sent`
  - `charge_created`
  - `charge_issued`
  - `charge_paid`
  - `invoice_attached`

`metadata` is event-specific and is rendered as provided.

