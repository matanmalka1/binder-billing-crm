# Authority Contact Module

> Last audited: 2026-04-13

Manages government-authority contacts for a client, such as tax office, VAT branch, and national insurance contacts. These records are used directly by the CRM and can be referenced by other domains such as `correspondence`.

## Scope

This module provides:
- CRUD for `authority_contacts`
- Filtering and pagination by client record and contact type
- Soft delete with audit fields (`deleted_at`, `deleted_by`)
- Role-based API access

## Domain Model

Implementation references:
- Model: `app/authority_contact/models/authority_contact.py`
- Schemas: `app/authority_contact/schemas/authority_contact.py`
- Repository: `app/authority_contact/repositories/authority_contact_repository.py`
- Service: `app/authority_contact/services/authority_contact_service.py`
- API: `app/authority_contact/api/authority_contact.py`

`AuthorityContact` fields:
- `id` (PK)
- `client_record_id` (FK -> `client_records.id`, required)
- `contact_type` (enum, required)
- `name` (required)
- `office`, `phone`, `email`, `notes` (optional)
- `created_at`, `updated_at`
- `deleted_at`, `deleted_by` (soft delete audit fields)

Contact type enum values:
- `assessing_officer`
- `vat_branch`
- `national_insurance`
- `other`

Notes:
- Contacts are client-record-scoped in the current implementation.
- The model does not currently include `business_id`.
- Reads exclude soft-deleted rows.

## API

The router is mounted via `app/router_registry.py` under `/api/v1` and uses a local router prefix of `/clients`, so the effective paths are:

### Create contact
- `POST /api/v1/clients/{client_record_id}/authority-contacts`
- Roles: `ADVISOR`, `SECRETARY`
- Body:

```json
{
  "contact_type": "vat_branch",
  "name": "Ms. VAT",
  "office": "Central",
  "phone": "03-0000000",
  "email": "vat@example.com",
  "notes": "Handles VAT filings"
}
```

### List contacts by client
- `GET /api/v1/clients/{client_record_id}/authority-contacts`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `contact_type` (optional enum)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

Response shape:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### Get contact
- `GET /api/v1/clients/authority-contacts/{contact_id}`
- Roles: `ADVISOR`, `SECRETARY`

### Update contact
- `PATCH /api/v1/clients/authority-contacts/{contact_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Partial update supported via `AuthorityContactUpdateRequest`

### Delete contact
- `DELETE /api/v1/clients/authority-contacts/{contact_id}`
- Role: `ADVISOR` only
- Soft delete
- Returns `204 No Content`

## Behavior Notes

- Creating/listing contacts validates that the client record exists and raises `CLIENT.NOT_FOUND` if it does not.
- `contact_type` is validated against the enum in both request parsing and service-level conversion.
- Get, update, and delete for unknown or soft-deleted contacts raise `AUTHORITY_CONTACT.NOT_FOUND`.
- Repository list and count operations are client-record-scoped and exclude soft-deleted records.
- Delete does not remove rows; it sets `deleted_at` and `deleted_by`.
- Results are ordered by `created_at DESC`.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors used here include:
- `CLIENT.NOT_FOUND`
- `AUTHORITY_CONTACT.NOT_FOUND`

## Cross-Domain Integration

`correspondence` can reference an authority contact via `contact_id` (`authority_contacts.id`).

That integration validates client-record ownership, not business ownership:
- the contact must exist
- the contact's `client_record_id` must match the correspondence `client_record_id`

Reference:
- `app/correspondence/services/correspondence_service.py`

## Tests

Authority-contact test suites currently present in the repository:
- `tests/authority_contact/api/test_authority_contact.py`
- `tests/authority_contact/service/test_authority_contact.py`
- `tests/authority_contact/repository/test_authority_contact_repository.py`

Run only this domain:

```bash
pytest tests/authority_contact -q
```
