# API Contract (Implemented Through Sprint 6)

This document is a **route index + high-level contract** for the API surface implemented through Sprint 6.
Behavioral rules (constraints, transitions, and invariants) remain **authoritatively defined** by the frozen sprint specifications:
- `SPRINT_3_FORMAL_SPECIFICATION.md` (billing)
- `sprint_4_formal_specification.md` + `sprint_4_freeze_rules.md` (notifications/documents/job)
- `SPRINT_5_FORMAL_SPECIFICATION.md` + `SPRINT_5_FREEZE_DECLARATION.md` (hardening)
- `SPRINT_6_FORMAL_SPECIFICATION.md` (operational readiness & UX enablement)

## Conventions
- Base path (business API): `/api/v1`
- Content type: `application/json`
- Auth: Bearer JWT (except `POST /auth/login`)
- Operational endpoints (no `/api/v1` prefix):
  - `GET /health`
  - `GET /info`

## Roles
- `ADVISOR`: admin-level access (super-role; may perform all `SECRETARY` actions)
- `SECRETARY`: operational-level access

## System / Ops
### `GET /health`
- Auth: none
- Purpose: readiness/health check (includes DB connectivity verification)

### `GET /info`
- Auth: none
- Response: `{ "app": "...", "env": "local|test|staging|production" }`

## Authentication
### `POST /api/v1/auth/login`
- Request: `email`, `password`
- Response `200`: `token`, `user { id, full_name, role }`

## Clients (ADVISOR + SECRETARY)
### `POST /api/v1/clients`

### `GET /api/v1/clients`
- Query params:
  - `status` (optional)
  - `page` (default: 1, min: 1)
  - `page_size` (default: 20, min: 1, max: 100)

### `GET /api/v1/clients/{client_id}`

### `PATCH /api/v1/clients/{client_id}`
- Authorization note: some status transitions are `ADVISOR`-only (see sprint specifications for the frozen rules).

## Binders (ADVISOR + SECRETARY)
### `POST /api/v1/binders/receive`

### `POST /api/v1/binders/{binder_id}/return`

### `GET /api/v1/binders`
- Query params:
  - `status` (optional)
  - `client_id` (optional)

### `GET /api/v1/binders/{binder_id}`

## Binder Operations (Sprint 2, ADVISOR + SECRETARY)

All Sprint 2 operational binder list endpoints are paginated:
- `page` (default: 1, min: 1)
- `page_size` (default: 20, min: 1, max: 100)

Response shape:
```json
{
  "items": [
    {
      "id": 1,
      "client_id": 123,
      "binder_number": "BND-2026-001",
      "status": "in_office",
      "received_at": "2026-01-01",
      "expected_return_at": "2026-04-01",
      "returned_at": null,
      "pickup_person_name": null,
      "is_overdue": true,
      "days_overdue": 38,
      "work_state": "waiting_for_work",
      "signals": ["overdue", "idle_binder"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 45
}
```

### `GET /api/v1/binders/open`
- Open binder definition: `status != returned`

### `GET /api/v1/binders/overdue`
- Overdue binder definition: `expected_return_at < today` AND `status != returned`

### `GET /api/v1/binders/due-today`
- Due today definition: `expected_return_at == today` AND `status != returned`

### `GET /api/v1/clients/{client_id}/binders`
- Lists binders for a specific client (same response + pagination as above)

### `GET /api/v1/binders/{binder_id}/history`
Response shape:
```json
{
  "binder_id": 1,
  "history": [
    {
      "old_status": "null",
      "new_status": "in_office",
      "changed_by": 1,
      "changed_at": "2026-01-01T10:00:00",
      "notes": "Binder received"
    }
  ]
}
```

## Dashboard (Sprint 1-2 Summary Endpoints)
### `GET /api/v1/dashboard/summary`
- Authorization: any authenticated user
- Response: `binders_in_office`, `binders_ready_for_pickup`, `binders_overdue`

### `GET /api/v1/dashboard/overview`
- Authorization: `ADVISOR` only
- Response: `total_clients`, `active_binders`, `overdue_binders`, `binders_due_today`, `binders_due_this_week`

## Dashboard Extended (Sprint 6, ADVISOR + SECRETARY)

### `GET /api/v1/dashboard/work-queue`
- Authorization: `ADVISOR` + `SECRETARY`
- Query params:
  - `page` (default: 1, min: 1)
  - `page_size` (default: 20, min: 1, max: 100)
- Response:
```json
{
  "items": [
    {
      "binder_id": 1,
      "client_id": 123,
      "client_name": "Example Corp",
      "binder_number": "BND-001",
      "work_state": "in_progress",
      "signals": ["near_sla"],
      "days_since_received": 15,
      "expected_return_at": "2026-03-01"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 45
}
```

### `GET /api/v1/dashboard/alerts`
- Authorization: `ADVISOR` + `SECRETARY`
- Response:
```json
{
  "items": [
    {
      "binder_id": 1,
      "client_id": 123,
      "client_name": "Example Corp",
      "binder_number": "BND-001",
      "alert_type": "overdue",
      "days_overdue": 5,
      "days_remaining": null
    }
  ],
  "total": 10
}
```

### `GET /api/v1/dashboard/attention`
- Authorization: `ADVISOR` + `SECRETARY`
- Note: Unpaid charges visible only to `ADVISOR`
- Response:
```json
{
  "items": [
    {
      "item_type": "idle_binder",
      "binder_id": 1,
      "client_id": 123,
      "client_name": "Example Corp",
      "description": "Binder BND-001 idle for 30 days"
    },
    {
      "item_type": "unpaid_charge",
      "binder_id": null,
      "client_id": 124,
      "client_name": "Another Corp",
      "description": "Unpaid charge: 1500 ILS"
    }
  ],
  "total": 15
}
```

## Timeline (Sprint 6, ADVISOR + SECRETARY)

### `GET /api/v1/clients/{client_id}/timeline`
- Authorization: `ADVISOR` + `SECRETARY`
- Query params:
  - `page` (default: 1, min: 1)
  - `page_size` (default: 50, min: 1, max: 200)
- Response:
```json
{
  "client_id": 123,
  "events": [
    {
      "event_type": "binder_received",
      "timestamp": "2026-01-15T10:00:00",
      "binder_id": 1,
      "charge_id": null,
      "description": "Binder BND-001 received",
      "metadata": {"binder_number": "BND-001"}
    },
    {
      "event_type": "charge_created",
      "timestamp": "2026-01-20T14:00:00",
      "binder_id": null,
      "charge_id": 5,
      "description": "Charge created: retainer",
      "metadata": {"amount": 1500.0, "status": "issued"}
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 125
}
```

## Search (Sprint 6, ADVISOR + SECRETARY)

### `GET /api/v1/search`
- Authorization: `ADVISOR` + `SECRETARY`
- Query params:
  - `query` (optional, general text search)
  - `client_name` (optional)
  - `id_number` (optional)
  - `binder_number` (optional)
  - `work_state` (optional: `waiting_for_work` | `in_progress` | `completed`)
  - `sla_state` (optional: `on_track` | `approaching` | `overdue`)
  - `signal_type` (optional, array: `missing_permanent_documents` | `near_sla` | `overdue` | `ready_for_pickup` | `unpaid_charges` | `idle_binder`)
  - `has_signals` (optional, boolean)
  - `page` (default: 1, min: 1)
  - `page_size` (default: 20, min: 1, max: 100)
- Response:
```json
{
  "results": [
    {
      "result_type": "binder",
      "client_id": 123,
      "client_name": "Example Corp",
      "binder_id": 1,
      "binder_number": "BND-001",
      "work_state": "in_progress",
      "signals": ["near_sla"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 35
}
```

## Charges (Sprint 3 Billing, ADVISOR + SECRETARY read)

Sprint 3 introduces internal billing via Charges. Behavioral rules and constraints are defined in `SPRINT_3_FORMAL_SPECIFICATION.md` (frozen).

### `POST /api/v1/charges` (ADVISOR only)
- Request:
  - `client_id` (int)
  - `amount` (number, must be > 0)
  - `charge_type` (string: `retainer` | `one_time`)
  - `period` (optional string: `YYYY-MM`)
  - `currency` (string, default `ILS`)
- Response `201`: `ChargeResponse`
- Errors:
  - `400` invalid input (e.g. amount <= 0) or `client_id` not found
  - `401` unauthenticated/invalid token
  - `403` forbidden (non-advisor)

### `GET /api/v1/charges` (ADVISOR + SECRETARY)
- Query params:
  - `client_id` (optional)
  - `status` (optional: `draft` | `issued` | `paid` | `canceled`)
  - `page` (default: 1, min: 1)
  - `page_size` (default: 20, min: 1, max: 100)
- Response `200`:
```json
{
  "items": [ { "id": 1 } ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

### `GET /api/v1/charges/{charge_id}` (ADVISOR + SECRETARY)
- Response `200`: `ChargeResponse`
- Errors:
  - `404` not found

### `POST /api/v1/charges/{charge_id}/issue` (ADVISOR only)
- Response `200`: `ChargeResponse`
- Errors:
  - `400` not found or invalid transition (only `draft` may be issued)

### `POST /api/v1/charges/{charge_id}/mark-paid` (ADVISOR only)
- Response `200`: `ChargeResponse`
- Errors:
  - `400` not found or invalid transition (only `issued` may be marked paid)

### `POST /api/v1/charges/{charge_id}/cancel` (ADVISOR only)
- Response `200`: `ChargeResponse`
- Errors:
  - `400` not found or invalid transition (cannot cancel `paid`; cannot re-cancel)

#### `ChargeResponse` shape
```json
{
  "id": 1,
  "client_id": 123,
  "amount": 1500.0,
  "currency": "ILS",
  "charge_type": "retainer",
  "period": "2026-02",
  "status": "draft",
  "created_at": "2026-02-09T12:00:00",
  "issued_at": null,
  "paid_at": null
}
```

## Permanent Documents (Sprint 4, ADVISOR + SECRETARY)

Sprint 4 introduces **permanent document presence tracking** (not full document management). See `sprint_4_formal_specification.md` for frozen behavior.

### `POST /api/v1/documents/upload`
- Content type: `multipart/form-data`
- Form fields:
  - `client_id` (int)
  - `document_type` (string; one of: `id_copy` | `power_of_attorney` | `engagement_agreement`)
  - `file` (upload)

### `GET /api/v1/documents/client/{client_id}`
- Lists permanent documents for a client.

### `GET /api/v1/documents/client/{client_id}/signals`
- Returns operational indicators for a client (advisory; non-blocking).

## Status Codes
- `200` success
- `201` created
- `400` bad request
- `401` unauthenticated/invalid token
- `403` forbidden
- `404` not found
- `409` conflict
