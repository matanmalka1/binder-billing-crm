# Frontend API Guide (Backend Frozen Through Sprint 6)

## Base URLs and Conventions

- Business API base path: `/api/v1`
- Operational endpoints (no `/api/v1` prefix):
  - `GET /health`
  - `GET /info`
  - `GET /` (service presence)
- Content type for JSON endpoints: `application/json`
- Upload endpoint uses `multipart/form-data`: `POST /api/v1/documents/upload`

## Authentication (JWT Bearer)

### Login

- Endpoint: `POST /api/v1/auth/login`
- Request body:
  - `email` (string)
  - `password` (string)
- Success response (`200`):
  - `token` (JWT string)
  - `user`:
    - `id` (int)
    - `full_name` (string)
    - `role` (`advisor` | `secretary`)

### Using the Token

For all authenticated endpoints, send:

- `Authorization: Bearer <token>`

JWT behavior:

- Tokens are signed with `HS256`.
- Tokens include `iat` and `exp` claims and expire.
- Token TTL is controlled by the `JWT_TTL_HOURS` environment variable.

## Required and Supported Headers

### Required (authenticated endpoints)

- `Authorization: Bearer <token>`

### Required (JSON request bodies)

- `Content-Type: application/json`

### Optional (request tracing)

- `X-Request-ID: <client-generated-id>`
  - If provided, the API uses this value.
  - If not provided, the API generates a UUID.
  - The API returns `X-Request-ID` in every response.

## Pagination (Implemented Shape)

The API uses `page` and `page_size` query parameters on paginated endpoints.

- `page` is 1-based (`ge=1`).
- `page_size` has endpoint-specific defaults and bounds:
  - Most paginated endpoints: default `20`, `1..100`
  - Timeline: default `50`, `1..200`

Pagination is implemented as:

- `offset = (page - 1) * page_size`

### `limit` / `offset` Query Params

`limit` and `offset` are not implemented as API query parameters. If sent, they are ignored as extra query parameters.

## Filtering Parameters (Search)

Endpoint: `GET /api/v1/search`

### `work_state`

`work_state` filters binder results by derived work state.

Accepted values:
- `waiting_for_work`
- `in_progress`
- `completed`

Behavior:
- If `work_state` is set to a value that does not match any derived binder work state, binder results are empty.

### `sla_state`

`sla_state` filters binder results using SLAService logic against binder timestamps.

Recognized values:
- `overdue`
- `approaching`
- `on_track`

Behavior:
- If `sla_state` is not one of the recognized values above, the SLA filter is not applied.

### `signal_type`

`signal_type` is a multi-value query parameter.

Encoding:
- Repeat the query key: `?signal_type=near_sla&signal_type=idle_binder`

Filter semantics:
- OR semantics: a binder matches if it has **any** of the requested signals.

Signals produced by binder signal computation:
- `overdue`
- `near_sla`
- `ready_for_pickup`
- `idle_binder`

### `has_signals`

`has_signals=true` filters binder results to binders with at least one computed binder signal.

Behavior:
- `has_signals=false` does not filter results.

## Error Handling Semantics

All errors use a consistent envelope:

```json
{
  "detail": "...",
  "error": {
    "type": "http_error|validation_error|database_error|server_error",
    "detail": "...",
    "status_code": 400
  }
}
```

Notes:

- `detail` is:
  - a string for most HTTP errors
  - a list of validation error objects for `422` validation failures
- The `error.detail` field is a string; for validation errors, it is `"Invalid request data"`.

### Status Codes (Observed Across the Frozen API)

- `400 Bad Request`
  - Invalid domain transitions and input rejected by service-layer rules (e.g., charge lifecycle transitions; binder return transition; invalid document type)
  - Some “not found” cases use `400` (e.g., issuing a missing charge returns `400` with a `"not found"` detail string)
- `401 Unauthorized`
  - Invalid or expired JWT token
  - Invalid login credentials
  - Unauthenticated requests to protected endpoints
- `403 Forbidden`
  - Authenticated user lacks required role (e.g., `SECRETARY` calling `ADVISOR`-only endpoints)
- `404 Not Found`
  - Resource is missing for endpoints that explicitly check existence (e.g., `GET /clients/{id}`, `GET /binders/{id}`, `GET /charges/{id}`, `GET /binders/{id}/history`, `GET /clients/{id}/binders`)
- `409 Conflict`
  - Uniqueness/business conflicts (e.g., creating a client with a duplicate `id_number`; receiving a binder when an active binder already exists with the same `binder_number`)

### `422 Unprocessable Entity` (Validation)

FastAPI request/query validation failures return `422` (e.g., missing required request body fields; `page < 1`; `page_size` outside allowed bounds).

## Retry and Idempotency Notes (Frontend-Safe Rules)

- GET endpoints are read-only and safe to retry.
- POST endpoints do not implement idempotency keys.
- Retrying a successful POST can create additional records or produce a state-transition error:
  - `POST /api/v1/charges` creates a new charge every time it succeeds.
  - `POST /api/v1/charges/{id}/issue`, `/mark-paid`, `/cancel` enforce lifecycle transitions; repeating a transition returns `400`.
  - `POST /api/v1/binders/receive` enforces “active binder number uniqueness” and returns `409` if an active binder already exists.

## What Frontend Never Computes or Infers

Frontend uses backend-derived fields as authoritative values and renders UI state from them.

Frontend does not compute or infer:

- `expected_return_at` (computed on binder intake)
- `days_in_office` (returned by binder endpoints)
- `days_since_received` (returned by `/dashboard/work-queue`)
- `is_overdue` / `days_overdue` (returned by operational binder endpoints)
- `work_state` (returned by operational binder endpoints, dashboard work queue, and search)
- `signals` (returned by operational binder endpoints, dashboard work queue, and search)
- “unpaid charges attention” (returned only via `/dashboard/attention` and only for `advisor`)
- Timeline ordering (timeline is returned already sorted by backend)

