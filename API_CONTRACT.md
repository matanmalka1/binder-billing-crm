# API Contract

## Conventions
- Base path: `/api/v1`
- Content type: `application/json`
- Auth: Bearer JWT (except login and health/info routes)

## Authentication
- `POST /api/v1/auth/login`
  - Request: `email`, `password`
  - Response `200`: `token`, `user { id, full_name, role }`

## Clients
- `POST /api/v1/clients` (advisor, secretary)
- `GET /api/v1/clients` (advisor, secretary)
- `GET /api/v1/clients/{client_id}` (advisor, secretary)
- `PATCH /api/v1/clients/{client_id}` (advisor, secretary)
  - Additional rule: status change to `frozen` or `closed` is advisor-only.

## Binders
- `POST /api/v1/binders/receive` (advisor, secretary)
- `POST /api/v1/binders/{binder_id}/return` (advisor, secretary)
- `GET /api/v1/binders` (advisor, secretary)
- `GET /api/v1/binders/{binder_id}` (advisor, secretary)

## Dashboard
- `GET /api/v1/dashboard/summary` (authenticated user)

## Status Codes
- `200` success
- `201` created
- `400` bad request
- `401` unauthenticated/invalid token
- `403` forbidden
- `404` not found
- `409` conflict
