# Businesses Module

> Last audited: 2026-04-13

`businesses` manages business activities that belong to a client. In the current model, the legal/tax identity lives on `clients`, while `Business` represents an operational activity under that client.

## Scope

This module is responsible for:
- Creating businesses under a client
- Listing and reading businesses for a client
- Updating business fields and lifecycle status
- Soft delete and restore
- Guard helpers used by downstream create flows
- Client status-card aggregation implemented in this domain

This module is not responsible for:
- Standalone `/api/v1/businesses/*` CRUD routes
- Client tax-profile CRUD
- A separate `BusinessTaxProfile` domain

## Domain Model

Implementation references:
- Model: `app/businesses/models/business.py`
- Schemas: `app/businesses/schemas/business_schemas.py`
- Repository: `app/businesses/repositories/business_repository.py`
- Read queries: `app/businesses/repositories/business_repository_read.py`
- API: `app/businesses/api/client_businesses_router.py`
- Service: `app/businesses/services/business_service.py`
- Update lifecycle: `app/businesses/services/business_update_service.py`
- Delete/restore lifecycle: `app/businesses/services/business_lifecycle_service.py`
- Guards: `app/businesses/services/business_guards.py`
- Status card: `app/businesses/services/status_card_service.py`

`Business` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `business_name` (required at DB level)
- `status` (`active`, `frozen`, `closed`)
- `opened_at` (required)
- `closed_at` (optional)
- `phone_override`, `email_override` (optional business-level contact overrides)
- `notes` (optional)
- `created_by`, `created_at`, `updated_at`
- `deleted_at`, `deleted_by`, `restored_at`, `restored_by`

Computed properties on the model:
- `full_name`
- `contact_phone`
- `contact_email`

Notes:
- Default repository reads exclude soft-deleted businesses.
- `contact_phone` and `contact_email` fall back to the linked client if no override is set on the business.
- A unique partial index prevents duplicate active `business_name` values per client.

## API

The router is mounted under `/api/v1`. The effective business endpoints are:

### Create business
- `POST /api/v1/clients/{client_id}/businesses`
- Roles: `ADVISOR` only

Request body:

```json
{
  "opened_at": "2026-04-13",
  "business_name": "North Branch",
  "notes": "Main operating activity"
}
```

Notes:
- `opened_at` is optional in the request; the service defaults it to `date.today()`.
- The response includes `available_actions`.

### List businesses for client
- `GET /api/v1/clients/{client_id}/businesses`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

Response shape:

```json
{
  "client_id": 123,
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### Get business
- `GET /api/v1/clients/{client_id}/businesses/{business_id}`
- Roles: `ADVISOR`, `SECRETARY`

### Update business
- `PATCH /api/v1/clients/{client_id}/businesses/{business_id}`
- Roles: `ADVISOR`, `SECRETARY`

Partial update fields:
- `business_name`
- `status`
- `notes`
- `closed_at`

Status transitions:
- setting status to `frozen` or `closed` requires `ADVISOR`
- setting status to `closed` defaults `closed_at` to today if omitted
- setting status to `active` clears `closed_at`

### Delete business
- `DELETE /api/v1/clients/{client_id}/businesses/{business_id}`
- Roles: `ADVISOR` only
- Soft delete
- Returns `204 No Content`

### Restore business
- `POST /api/v1/clients/{client_id}/businesses/{business_id}/restore`
- Roles: `ADVISOR` only

Behavior:
- verifies ownership against the provided `client_id`
- restores a soft-deleted business
- sets status back to `active`

## Business Rules

- Creating a business validates that the client exists; missing clients raise `CLIENT.NOT_FOUND`.
- If the client has at least one non-deleted business and all of them are `closed`, creating another business raises `BUSINESS.CLIENT_ALL_CLOSED`.
- Creating a business with a duplicate active `business_name` for the same client raises `BUSINESS.NAME_CONFLICT`.
- Generic DB-level duplication during create is surfaced as `BUSINESS.CONFLICT`.
- Unknown businesses, or businesses not owned by the route `client_id`, raise `BUSINESS.NOT_FOUND`.
- Restoring a business that is not deleted raises `BUSINESS.NOT_DELETED`.
- Non-advisors attempting restricted lifecycle operations raise `BUSINESS.FORBIDDEN`.

## Guard Helpers

Downstream create flows can use:
- `get_business_or_raise`
- `assert_business_allows_create`
- `validate_business_for_create`

Guard behavior:
- `active` => allowed
- `frozen` => raises `BUSINESS.FROZEN`
- `closed` => raises `BUSINESS.CLOSED`

## Status Card

This domain also contains the client status-card aggregation service used by:
- `GET /api/v1/clients/{client_id}/status-card`

That endpoint is client-scoped. `status_card_service.py` aggregates:
- VAT summary
- annual report summary
- issued charges summary
- advance payments summary
- binder summary
- permanent-document summary

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Common domain error codes here include:
- `CLIENT.NOT_FOUND`
- `BUSINESS.NOT_FOUND`
- `BUSINESS.NAME_CONFLICT`
- `BUSINESS.CONFLICT`
- `BUSINESS.CLIENT_ALL_CLOSED`
- `BUSINESS.NOT_DELETED`
- `BUSINESS.FORBIDDEN`
- `BUSINESS.CLOSED`
- `BUSINESS.FROZEN`
- `BUSINESS.INVALID_STATUS`

## Tests

Business-domain test suites currently present in the repository:
- `tests/businesses/service/test_business_service.py`
- `tests/businesses/service/test_business_service_additional.py`
- `tests/businesses/service/test_business_guards.py`
- `tests/businesses/api/test_business_binders_api.py`
- `tests/actions/test_business_actions.py`

Run business-related tests:

```bash
pytest tests/businesses tests/actions/test_business_actions.py -q
```
