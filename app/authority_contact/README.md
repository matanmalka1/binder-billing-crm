# Authority Contact Module

> Last audited: 2026-03-22 (domain-by-domain backend sync).

Manages per-business authority contacts (tax office, VAT branch, national insurance, etc.) used by the CRM and referenced by other domains (for example correspondence entries).

## Scope

This module provides:
- CRUD for `authority_contacts`
- Filtering + pagination by business and contact type
- Soft delete with audit fields (`deleted_at`, `deleted_by`)
- Role-based API access

## Domain Model

`AuthorityContact` fields:
- `id` (PK)
- `business_id` (FK -> `businesses.id`, required)
- `contact_type` (enum, required)
- `name` (required)
- `office`, `phone`, `email`, `notes` (optional)
- `created_at`, `updated_at`
- `deleted_at`, `deleted_by` (for soft delete)

Contact type enum values:
- `assessing_officer`
- `vat_branch`
- `national_insurance`
- `other`

Implementation references:
- Model: `app/authority_contact/models/authority_contact.py`
- Schemas: `app/authority_contact/schemas/authority_contact.py`
- Repository: `app/authority_contact/repositories/authority_contact_repository.py`
- Service: `app/authority_contact/services/authority_contact_service.py`
- API: `app/authority_contact/api/authority_contact.py`

## API

Router prefix is `/api/v1/businesses` (mounted in `app/main.py`).

### Create contact
- `POST /api/v1/businesses/{business_id}/authority-contacts`
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

### List contacts by business
- `GET /api/v1/businesses/{business_id}/authority-contacts`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `contact_type` (optional enum)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

### Get contact
- `GET /api/v1/businesses/authority-contacts/{contact_id}`
- Roles: `ADVISOR`, `SECRETARY`

### Update contact
- `PATCH /api/v1/businesses/authority-contacts/{contact_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Partial update supported.

### Delete contact (soft delete)
- `DELETE /api/v1/businesses/authority-contacts/{contact_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

## Behavior Notes

- Creating a contact validates that the business exists (`BUSINESS.NOT_FOUND` on missing business).
- `contact_type` is validated against the enum; invalid values return a validation error.
- Get, update, and delete for unknown or soft-deleted contacts raise `AUTHORITY_CONTACT.NOT_FOUND`.
- Repository reads (`get_by_id`, list/count) exclude soft-deleted records.
- Delete does not remove rows; it sets `deleted_at` + `deleted_by`.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `BUSINESS.NOT_FOUND`
- `AUTHORITY_CONTACT.NOT_FOUND`

## Cross-Domain Integration

`correspondence` can reference an authority contact via `contact_id` (`authority_contacts.id`).
When used, correspondence service enforces that the contact belongs to the same business.

## Tests

Authority-contact test suites:
- `tests/authority_contact/api/test_authority_contact.py`
- `tests/authority_contact/service/test_authority_contact.py`
- `tests/authority_contact/repository/test_authority_contact_repository.py`
- `tests/authority_contact/model/test_authority_contact_model.py`

Run only this domain:

```bash
pytest tests/authority_contact -q
```
