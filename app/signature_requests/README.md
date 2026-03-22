# Signature Requests Module

> Last audited: 2026-03-22

Manages the digital-signature request lifecycle for business documents and approvals, including advisor workflows, public signer token flows, and immutable audit events.

## Audit Summary

- Router wiring is valid:
  - Authenticated routes are included under `/api/v1`.
  - Public signer routes are exposed under `/sign/*` without JWT.
- Service/repository flow is consistent and covered by tests.
- Domain naming is `business` (not `client`) in request fields and list routes.
- Test suite for this domain passes: `27 passed`.

## Scope

This module provides:
- Signature request creation in `draft` state
- Sending request links with expiring signing tokens
- Public signer actions (`view`, `approve`, `decline`)
- Advisor actions (`cancel`, `audit trail`, `pending list`)
- Business-scoped signature request listing
- Automatic expiry handling for overdue pending requests
- Immutable audit event logging per lifecycle action

## Domain Model

### `SignatureRequest`

Core fields:
- `id` (PK)
- `business_id` (FK -> `businesses.id`, required)
- `created_by` (FK -> `users.id`, required)
- Optional links:
  - `annual_report_id` (FK -> `annual_reports.id`)
  - `document_id` (FK -> `permanent_documents.id`)
- Request metadata:
  - `request_type`
  - `title`, `description`
  - `content_hash`, `storage_key`
- Signer metadata:
  - `signer_name`
  - `signer_email`, `signer_phone`
- Lifecycle fields:
  - `status`
  - `signing_token`
  - `sent_at`, `expires_at`, `signed_at`, `declined_at`, `canceled_at`
  - `canceled_by`
  - `signer_ip_address`, `signer_user_agent`, `decline_reason`
  - `signed_document_key`

Status enum values:
- `draft`
- `pending_signature`
- `signed`
- `declined`
- `expired`
- `canceled`

Request type enum values:
- `engagement_agreement`
- `annual_report_approval`
- `power_of_attorney`
- `vat_return_approval`
- `custom`

### `SignatureAuditEvent`

Append-only audit trail fields:
- `id` (PK)
- `signature_request_id` (FK)
- `event_type`
- `actor_type` (`advisor|signer|system`)
- `actor_id`, `actor_name`
- `ip_address`, `user_agent`
- `notes`
- `occurred_at`

Implementation references:
- Model: `app/signature_requests/models/signature_request.py`
- Schemas: `app/signature_requests/schemas/signature_request.py`
- Repository: `app/signature_requests/repositories/signature_request_repository.py`
- Services: `app/signature_requests/services/`
- APIs: `app/signature_requests/api/routes_advisor.py`, `app/signature_requests/api/routes_client.py`, `app/signature_requests/api/routes_signer.py`

## API

Mounted from `app/router_registry.py`:
- Authenticated signature routes: `app.include_router(signature_requests_routers.router, prefix="/api/v1")`
- Public signer routes: `app.include_router(signature_requests_routers.signer_router)`

### Advisor routes (`/api/v1/signature-requests`)

Roles: `ADVISOR`, `SECRETARY`

- `POST /api/v1/signature-requests`
  - Create request (initial status: `draft`)
- `GET /api/v1/signature-requests/pending`
  - List `pending_signature` requests (paginated)
- `GET /api/v1/signature-requests/{request_id}`
  - Get request details with embedded audit trail
- `GET /api/v1/signature-requests/{request_id}/audit-trail`
  - Get audit events only
- `POST /api/v1/signature-requests/{request_id}/send`
  - Move `draft -> pending_signature`, generate token and expiry
  - Returns `signing_token` and `signing_url_hint`
- `POST /api/v1/signature-requests/{request_id}/cancel`
  - Cancel request (allowed from `draft`/`pending_signature`)

### Business-scoped listing (`/api/v1/businesses/{business_id}/signature-requests`)

Roles: `ADVISOR`, `SECRETARY`

- `GET /api/v1/businesses/{business_id}/signature-requests`
- Query params:
  - `status` (optional)
  - `page` (default `1`)
  - `page_size` (default `20`, max `100`)

### Public signer routes (`/sign/{token}`)

Auth: no JWT (token-based)

- `GET /sign/{token}`
  - Records `viewed` audit event
- `POST /sign/{token}/approve`
  - Signs request (`pending_signature -> signed`)
- `POST /sign/{token}/decline`
  - Declines request (`pending_signature -> declined`)

## Behavior Notes

- `send` is valid only in `draft` status; otherwise `SIGNATURE_REQUEST.INVALID_STATUS`.
- `send` generates a one-time token (`secrets.token_urlsafe(32)`) and default expiry is 14 days.
- Signing token is cleared after approve/decline/cancel/expire.
- Signer actions require:
  - status `pending_signature`
  - not expired
- Runtime expiry handling:
  - If signer action occurs after expiry, request is auto-marked `expired` and `SIGNATURE_REQUEST.EXPIRED` is returned.
- Batch expiry handling:
  - `expire_overdue_requests()` marks overdue pending requests as `expired` and appends audit events.
- Create request behavior:
  - Validates business exists (`BUSINESS.NOT_FOUND`).
  - Validates `request_type` (`SIGNATURE_REQUEST.INVALID_TYPE`).
  - Optionally computes SHA-256 `content_hash` from `content_to_hash`.
  - Falls back signer email/phone from business profile when missing.
- Audit trail is append-only and records events such as `created`, `sent`, `viewed`, `signed`, `declined`, `canceled`, `expired`.
- Annual report integration:
  - Signing an annual-report approval can auto-transition annual report status from `pending_client` to `submitted` (best effort).

## Error Envelope

Errors follow global app error format (`app/core/exceptions.py`) with fields like:
- `detail`
- `error`
- `error_meta`

Common domain error codes:
- `SIGNATURE_REQUEST.NOT_FOUND`
- `SIGNATURE_REQUEST.INVALID_TYPE`
- `SIGNATURE_REQUEST.INVALID_STATUS`
- `SIGNATURE_REQUEST.TOKEN_INVALID`
- `SIGNATURE_REQUEST.EXPIRED`
- `BUSINESS.NOT_FOUND`

## Cross-Domain Integration

- `businesses` integration:
  - Request creation/listing is business-scoped; contact fallback uses business email/phone.
- `annual_reports` integration:
  - Signed annual-report approval can trigger automatic status transition and `client_approved_at` update.
- `permanent_documents` integration:
  - Requests may reference `document_id`/`storage_key` for document context.
- `users` integration:
  - Advisor identity is captured in `created_by` and audit actor fields.

## Tests

Signature-requests test suites:
- `tests/signature_requests/api/test_signature_requests.py`
- `tests/signature_requests/api/test_signature_requests_cancel_and_client_list.py`
- `tests/signature_requests/service/test_signature_requests.py`
- `tests/signature_requests/service/test_signer_actions_auto_advance.py`
- `tests/signature_requests/repository/test_signature_request_repository.py`
- `tests/signature_requests/repository/test_signature_request_repository_list_by_client.py`

Run only this domain:

```bash
pytest tests/signature_requests -q
```
