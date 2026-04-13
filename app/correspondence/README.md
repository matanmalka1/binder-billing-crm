# Correspondence Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages per-client correspondence entries (calls, letters, emails, meetings) used by the CRM timeline/context and linked to optional authority contacts.

## Scope

This module provides:
- CRUD for `correspondence_entries`
- Filtering + pagination by client
- Descending timeline ordering by `occurred_at`
- Soft delete with audit fields (`deleted_at`, `deleted_by`)
- Role-based API access
- Validation of contact ownership when `contact_id` is provided

## Domain Model

`Correspondence` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `contact_id` (FK -> `authority_contacts.id`, optional)
- `correspondence_type` (enum, required)
- `subject` (required)
- `notes` (optional)
- `occurred_at` (required)
- `created_by` (FK -> `users.id`, required)
- `created_at`
- `deleted_at`, `deleted_by` (for soft delete)

Correspondence type enum values:
- `call`
- `letter`
- `email`
- `meeting`

Implementation references:
- Model: `app/correspondence/models/correspondence.py`
- Schemas: `app/correspondence/schemas/correspondence.py`
- Repository: `app/correspondence/repositories/correspondence_repository.py`
- Service: `app/correspondence/services/correspondence_service.py`
- API: `app/correspondence/api/correspondence.py`

## API

Router prefix is `/api/v1/clients` (mounted in `app/main.py`).

### Create correspondence entry
- `POST /api/v1/clients/{client_id}/correspondence`
- Roles: `ADVISOR`, `SECRETARY`
- Body:

```json
{
  "business_id": 12,
  "contact_id": 10,
  "correspondence_type": "call",
  "subject": "Status check",
  "notes": "Asked about refund ETA",
  "occurred_at": "2026-03-16T10:00:00"
}
```

### List correspondence entries by client
- `GET /api/v1/clients/{client_id}/correspondence`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `business_id` (optional; filter client entries to one business context)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

### Get correspondence entry
- `GET /api/v1/clients/{client_id}/correspondence/{correspondence_id}`
- Roles: `ADVISOR`, `SECRETARY`

### Update correspondence entry
- `PATCH /api/v1/clients/{client_id}/correspondence/{correspondence_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Partial update supported, including optional `business_id` reassignment within the same client.

### Delete correspondence entry (soft delete)
- `DELETE /api/v1/clients/{client_id}/correspondence/{correspondence_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

## Behavior Notes

- Creating an entry validates that the client exists (`CLIENT.NOT_FOUND` on missing client).
- If `business_id` is provided, it must belong to the same client (`BUSINESS.NOT_FOUND` / `CORRESPONDENCE.FORBIDDEN_BUSINESS` on mismatch).
- `correspondence_type` is validated against enum values; invalid values return `400`.
- If `contact_id` is provided, service enforces contact belongs to the same client (`CORRESPONDENCE.FORBIDDEN_CONTACT` on mismatch/missing).
- Get/update/delete for unknown or cross-client entries return `CORRESPONDENCE.NOT_FOUND`.
- Repository reads (`get_by_id`, list/count) exclude soft-deleted records.
- List is ordered by `occurred_at` descending (latest first), unless `sort_dir=asc`.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `CORRESPONDENCE.NOT_FOUND`
- `CORRESPONDENCE.FORBIDDEN_CONTACT`
- `CORRESPONDENCE.FORBIDDEN_BUSINESS`
- `CLIENT.NOT_FOUND`
- `BUSINESS.NOT_FOUND`

## Cross-Domain Integration

- `authority_contact` integration: `contact_id` links a correspondence entry to an authority contact and is validated for same-client ownership.
- `clients` integration: correspondence is client-scoped and exposed under `/clients/{client_id}/correspondence`.
- `businesses` integration: `business_id` remains optional context for UI grouping/filtering inside a client.

## Tests

Correspondence test suites:
- `tests/correspondence/api/test_correspondence.py`
- `tests/correspondence/api/test_correspondence_update_delete.py`
- `tests/correspondence/repository/test_correspondence_repository.py`

Run only this domain:

```bash
pytest tests/correspondence -q
```
