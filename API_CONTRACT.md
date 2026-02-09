# API Contract (Frozen Through Sprint 2)

This document describes the API surface implemented through Sprint 2.
Sprint 3 scope (if any) is defined only in `SPRINT_3_FORMAL_SPECIFICATION.md`.

## Conventions
- Base path: `/api/v1`
- Content type: `application/json`
- Auth: Bearer JWT (except `POST /auth/login`)

## Roles
- `ADVISOR`: admin-level access
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

## Status Codes
- `200` success
- `201` created
- `400` bad request
- `401` unauthenticated/invalid token
- `403` forbidden
- `404` not found
- `409` conflict
