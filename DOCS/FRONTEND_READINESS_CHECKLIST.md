# Frontend Readiness Checklist (Sprint 7 Documentation-Only)

## Endpoints That Exist (Implemented Through Sprint 6)

Unauthenticated:

- `GET /`
- `GET /health`
- `GET /info`
- `POST /api/v1/auth/login`

Clients:

- `POST /api/v1/clients`
- `GET /api/v1/clients` (paginated: `page`, `page_size`)
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`

Binders:

- `POST /api/v1/binders/receive`
- `POST /api/v1/binders/{binder_id}/return`
- `GET /api/v1/binders` (not paginated)
- `GET /api/v1/binders/{binder_id}`

Operational binder lists (paginated):

- `GET /api/v1/binders/open`
- `GET /api/v1/binders/overdue`
- `GET /api/v1/binders/due-today`
- `GET /api/v1/clients/{client_id}/binders`

Binder history:

- `GET /api/v1/binders/{binder_id}/history`

Dashboards:

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/overview` (advisor-only)
- `GET /api/v1/dashboard/work-queue` (paginated)
- `GET /api/v1/dashboard/alerts`
- `GET /api/v1/dashboard/attention`

Search and timeline:

- `GET /api/v1/search` (paginated)
- `GET /api/v1/clients/{client_id}/timeline` (paginated)

Charges:

- `GET /api/v1/charges` (paginated)
- `GET /api/v1/charges/{charge_id}`
- `POST /api/v1/charges` (advisor-only)
- `POST /api/v1/charges/{charge_id}/issue` (advisor-only)
- `POST /api/v1/charges/{charge_id}/mark-paid` (advisor-only)
- `POST /api/v1/charges/{charge_id}/cancel` (advisor-only)

Permanent documents:

- `POST /api/v1/documents/upload` (`multipart/form-data`)
- `GET /api/v1/documents/client/{client_id}`
- `GET /api/v1/documents/client/{client_id}/signals`

## Endpoints That Intentionally Do Not Exist (Confirmed by Route Set)

- No endpoint to mark a binder `ready_for_pickup` (no `POST /api/v1/binders/{id}/ready-for-pickup`)
- No notifications listing endpoint (no `GET /api/v1/notifications`)
- No invoices API (no `GET /api/v1/invoices`, no `POST /api/v1/invoices`)
- No “update charge” endpoint (no `PATCH /api/v1/charges/{id}`)
- No delete endpoints for clients/binders/charges/documents
- No “SLA state” endpoint; SLA UI state is returned via alerts/signals and operational list fields
- No idempotency-key support endpoints or headers

## Frontend Must Not Assume

- Stable ordering of:
  - `/api/v1/search` results
  - `/api/v1/dashboard/work-queue` items
- Existence checks for timeline:
  - `/api/v1/clients/{client_id}/timeline` returns `200` with `events: []` when there are no events; it does not enforce `client_id` existence.
- That `has_signals=false` filters to binders without signals:
  - Only `has_signals=true` applies filtering.
- That `sla_state` rejects invalid values:
  - Unknown `sla_state` values do not apply an SLA filter.
- That `signal_type` accepts comma-separated lists:
  - `signal_type` is parsed as repeated query keys.

## What Always Comes From Backend

- Work queues, alerts, attention lists
- Work state (`work_state`)
- Signals (`signals`)
- SLA day counters (`days_overdue`, `days_remaining`, `days_since_received`)
- Timeline event ordering and event typing (`event_type`)
- Role-based response shaping for charges (secretary does not receive `amount`/`currency` in charges endpoints)
- Request tracing header behavior (`X-Request-ID` is returned on responses)

## Common Frontend Mistakes to Avoid

- Sending `limit`/`offset` for pagination and expecting pagination to work
- Recomputing SLA from binder dates instead of reading backend fields/signals/alerts
- Treating `binder.status` as equivalent to SLA overdue state
- Expecting `POST /api/v1/charges/{id}/issue` “not found” to return `404` (it returns `400` with a `"not found"` detail string)
- Hardcoding attention item types beyond:
  - `idle_binder`
  - `ready_for_pickup`
  - `unpaid_charge` (advisor-only)

