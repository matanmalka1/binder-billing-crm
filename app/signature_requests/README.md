# Signature Requests Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages digital signature request lifecycle for client documents and approvals, including advisor workflows, public signer token flows, and immutable audit trail events.

## Scope

This module provides:
- Signature request creation in draft state
- Sending request links with expiring signing tokens
- Public signer actions (view / approve / decline)
- Advisor actions (cancel, audit trail, pending list)
- Client-scoped signature request listing
- Automatic expiry handling for overdue pending requests
- Immutable audit event logging per lifecycle action

## Domain Model

### `SignatureRequest`

Core fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
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
- Repository: `app/signature_requests/repositories/signature_request_repository.py` (+ CRUD/Audit mixins)
- Services: `app/signature_requests/services/` (advisor, signer, and expiry flows)
- APIs: `app/signature_requests/api/routes_advisor.py`, `app/signature_requests/api/routes_client.py`, `app/signature_requests/api/routes_signer.py`

## API

Mounted in `app/main.py` as:
- Advisor/client authenticated routers with `/api/v1` prefix
- Public signer router without `/api/v1` prefix

### Advisor routes (`/api/v1/signature-requests`)

Roles: `ADVISOR`, `SECRETARY`

- `POST /api/v1/signature-requests`
  - Create request (initial status: `draft`)
- `GET /api/v1/signature-requests/pending`
  - List pending-signature requests (paginated)
- `GET /api/v1/signature-requests/{request_id}`
  - Get request details with embedded audit trail
- `GET /api/v1/signature-requests/{request_id}/audit-trail`
  - Get audit events only
- `POST /api/v1/signature-requests/{request_id}/send`
  - Move `draft -> pending_signature`, generate token and expiry
  - Returns one-time token field and signing URL hint
- `POST /api/v1/signature-requests/{request_id}/cancel`
  - Cancel request (allowed from `draft`/`pending_signature`)

### Client-scoped listing (`/api/v1/clients/{client_id}/signature-requests`)

Roles: `ADVISOR`, `SECRETARY`

- `GET /api/v1/clients/{client_id}/signature-requests`
- Query params:
  - `status` (optional)
  - `page` (default `1`)
  - `page_size` (default `20`, max `100`)

### Public signer routes (`/sign/{token}`)

Auth: no JWT (token-based)

- `GET /sign/{token}`
  - Record signer view event
- `POST /sign/{token}/approve`
  - Sign request (`pending_signature -> signed`)
- `POST /sign/{token}/decline`
  - Decline request (`pending_signature -> declined`)

## Behavior Notes

- `send` action is valid only in `draft` status; otherwise `SIGNATURE_REQUEST.INVALID_STATUS`.
- Signing token is generated on send and cleared after approve/decline/cancel/expire.
- Signer actions require signable request state:
  - Must be `pending_signature`
  - Must not be expired
- Expiry handling:
  - Runtime sign attempt on expired request auto-marks `expired` and returns `SIGNATURE_REQUEST.EXPIRED`.
  - System/admin flow can batch expire overdue pending requests.
- Create request behavior:
  - Validates client exists.
  - Validates `request_type` value.
  - Optionally computes SHA-256 `content_hash` from `content_to_hash`.
  - Falls back signer email/phone from client profile when missing.
- Audit trail is append-only and records events such as `created`, `sent`, `viewed`, `signed`, `declined`, `canceled`, `expired`.
- Annual report integration:
  - Signing annual-report approval can auto-transition annual report status from `pending_client` to `submitted` (best-effort system action).

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `SIGNATURE_REQUEST.NOT_FOUND`
- `SIGNATURE_REQUEST.INVALID_STATUS`
- `SIGNATURE_REQUEST.TOKEN_INVALID`
- `SIGNATURE_REQUEST.EXPIRED`

## Cross-Domain Integration

- `clients` integration:
  - Request creation/listing is client-scoped; contact info fallback uses client email/phone.
- `annual_reports` integration:
  - Signed annual-report approval can trigger automatic status transition and approval timestamp updates.
- `permanent_documents` integration:
  - Requests may reference `document_id`/`storage_key` for signed content context.
- `users` integration:
  - Advisor identity captured in `created_by` and audit actor fields.

## Tests

Signature-requests test suites:
- `tests/signature_requests/api/test_signature_requests.py`
- `tests/signature_requests/service/test_signature_requests.py`
- `tests/signature_requests/repository/test_signature_request_repository.py`

Run only this domain:

```bash
pytest tests/signature_requests -q
```
