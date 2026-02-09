# API Contract (Implemented Through Sprint 3)

This document describes the API surface implemented through Sprint 3.

Sprint 4 behavior is governed only by the Sprint 4 documents and is not described here.

## Conventions
- Base path: `/api/v1`
- Content type: `application/json`
- Auth: Bearer JWT (except `POST /auth/login`)

## Roles
- `ADVISOR`: admin-level access (super-role; may perform all `SECRETARY` actions)
- `SECRETARY`: operational-level access

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
- Additional rule: status change to `frozen` or `closed` is `ADVISOR`-only.

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
      "days_overdue": 38
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 45
}
```

### `GET /api/v1/binders/open`
- Open binder definition: `status != RETURNED`

### `GET /api/v1/binders/overdue`
- Overdue binder definition: `expected_return_at < today` AND `status != RETURNED`

### `GET /api/v1/binders/due-today`
- Due today definition: `expected_return_at == today` AND `status != RETURNED`

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

## Dashboard
### `GET /api/v1/dashboard/summary`
- Authorization: any authenticated user
- Response: `binders_in_office`, `binders_ready_for_pickup`, `binders_overdue`

### `GET /api/v1/dashboard/overview`
- Authorization: `ADVISOR` only
- Response: `total_clients`, `active_binders`, `overdue_binders`, `binders_due_today`, `binders_due_this_week`

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

### `GET /api/v1/charges/{id}` (ADVISOR + SECRETARY)
- Response `200`: `ChargeResponse`
- Errors:
  - `404` not found

### `POST /api/v1/charges/{id}/issue` (ADVISOR only)
- Response `200`: `ChargeResponse`
- Errors:
  - `400` not found or invalid transition (only `draft` may be issued)

### `POST /api/v1/charges/{id}/mark-paid` (ADVISOR only)
- Response `200`: `ChargeResponse`
- Errors:
  - `400` not found or invalid transition (only `issued` may be marked paid)

### `POST /api/v1/charges/{id}/cancel` (ADVISOR only)
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

## Status Codes
- `200` success
- `201` created
- `400` bad request
- `401` unauthenticated/invalid token
- `403` forbidden
- `404` not found
- `409` conflict
