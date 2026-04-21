# Correspondence Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages per-client-record correspondence entries (calls, letters, emails, meetings, faxes) used by the CRM timeline/context and linked to optional business context and authority contacts.

## Scope

This module provides:
- CRUD for `correspondence_entries`
- Filtering + pagination by client record
- Descending timeline ordering by `occurred_at`
- Soft delete with audit fields (`deleted_at`, `deleted_by`)
- Role-based API access
- Optional business scoping via `business_id`
- Validation of contact ownership when `contact_id` is provided

## Domain Model

`Correspondence` fields:
- `id` (PK)
- `client_record_id` (FK -> `client_records.id`, required)
- `business_id` (FK -> `businesses.id`, optional)
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
- `fax`

Implementation references:
- Model: `app/correspondence/models/correspondence.py`
- Schemas: `app/correspondence/schemas/correspondence.py`
- Repository: `app/correspondence/repositories/correspondence_repository.py`
- Service: `app/correspondence/services/correspondence_service.py`
- API: `app/correspondence/api/correspondence.py`

## API

Router prefix is `/api/v1/clients` (mounted via `app/router_registry.py`).

### Create correspondence entry
- `POST /api/v1/clients/{client_record_id}/correspondence`
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
- `GET /api/v1/clients/{client_record_id}/correspondence`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `business_id` (optional; filter client entries to one business context)
  - `correspondence_type` (optional)
  - `contact_id` (optional)
  - `from_date` (optional)
  - `to_date` (optional)
  - `sort_dir` (`asc` or `desc`, default `desc`)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

### Get correspondence entry
- `GET /api/v1/clients/{client_record_id}/correspondence/{correspondence_id}`
- Roles: `ADVISOR`, `SECRETARY`

### Update correspondence entry
- `PATCH /api/v1/clients/{client_record_id}/correspondence/{correspondence_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Partial update supported for `business_id`, `contact_id`, `correspondence_type`, `subject`, `notes`, and `occurred_at`.
- `business_id` can be reassigned within the same client.

### Delete correspondence entry (soft delete)
- `DELETE /api/v1/clients/{client_record_id}/correspondence/{correspondence_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

## Behavior Notes

- Creating an entry validates that the client record exists (`CLIENT.NOT_FOUND` on missing client record).
- If `business_id` is provided, it must belong to the same legal entity as the client record (`BUSINESS.NOT_FOUND` / `BUSINESS.FORBIDDEN_LEGAL_ENTITY` on mismatch).
- `correspondence_type` is validated against enum values; invalid values return `400`.
- If `contact_id` is provided, service enforces contact belongs to the same client record (`CORRESPONDENCE.FORBIDDEN_CONTACT` on mismatch/missing).
- `occurred_at` cannot be in the future; schema validation rejects future timestamps.
- Get/update/delete for unknown or cross-client entries return `CORRESPONDENCE.NOT_FOUND`.
- Repository reads (`get_by_id`, list/count) exclude soft-deleted records.
- List supports filtering by `business_id`, `correspondence_type`, `contact_id`, and date range (`from_date`, `to_date`).
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

- `authority_contact` integration: `contact_id` links a correspondence entry to an authority contact and is validated for same-client-record ownership.
- `clients` integration: correspondence is client-record-scoped and exposed under `/clients/{client_record_id}/correspondence`.
- `businesses` integration: `business_id` remains optional context for UI grouping/filtering inside a client.

## Tests

Correspondence test suites:
- `tests/correspondence/api/test_correspondence.py`
- `tests/correspondence/api/test_correspondence_update_delete.py`
- `tests/correspondence/service/test_correspondence_service_additional.py`
- `tests/correspondence/repository/test_correspondence_repository.py`
- `tests/correspondence/test_correspondence_schemas.py`

Run only this domain:

```bash
pytest tests/correspondence -q
```
