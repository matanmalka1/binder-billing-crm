## Scope
This file owns only:
- Backend-local API contract details, examples, and migration notes.
- Detailed status-code, DTO, and action-response conventions subordinate to canonical YM_Docs API contract rules.

This file must not contain:
- API rules that override `../docs/docs/architecture/api-contracts.md`.
- Legacy compatibility policy that conflicts with ADR-0001.
- Frontend implementation rules.

Source of truth: reference

Canonical project-wide rules:
- `../../docs/docs/architecture/api-contracts.md`
- `../../docs/docs/workflow/verification.md`

# API Contract Standard

This document defines the target public API contract for backend endpoints.
Internal implementation may differ by domain, but externally visible request and response contracts must be consistent.

## Applicability

This standard applies to endpoints that expose application resources through `/api/v1/*`.

It is mandatory for list endpoints that power tables, queues, feeds, cards with paging, and selectable resource lists.
It does not need to apply to:

- `GET /{id}` single-resource reads
- dashboard summaries and statistics
- exports and downloads
- auth flows
- narrow autocomplete/search endpoints with their own documented contract
- write-only action endpoints that do not return lists

## URL Naming

Use plural resource names and clear nested resources.

Good:

```txt
/api/v1/clients
/api/v1/clients/{client_id}
/api/v1/binders/{binder_id}/mark-ready-for-handover
/api/v1/notifications/preview
/api/v1/notifications/send
```

Do not use RPC-style or mixed-case paths:

```txt
/getClients
/client/list
/binderReady
/send_notification
```

Rule: resources are nouns, usually plural. Business actions may use verbs only when they represent a real domain transition or command.

## HTTP Methods

Use methods consistently:

| Method | Use |
|--------|-----|
| `GET` | read/list only |
| `POST` | create or business action |
| `PATCH` | partial update |
| `PUT` | full replacement, rarely needed |
| `DELETE` | delete or soft delete |

Never use `GET` for state-changing operations.

Bad:

```txt
GET /binders/{binder_id}/complete
```

Good:

```txt
POST /binders/{binder_id}/complete
```

## List Request Contract

Every standard list endpoint accepts:

```txt
page
page_size
sort_by
order
```

Example:

```txt
GET /api/v1/annual-reports?page=1&page_size=25&sort_by=created_at&order=desc
```

Parameter rules:

| Parameter | Rule |
|-----------|------|
| `page` | `int`, default `1`, minimum `1` |
| `page_size` | `int`, bounded; default should match the UI, usually `20` or `25` |
| `sort_by` | allowlisted field name only |
| `order` | only `asc` or `desc` |

Do not introduce alias parameter names for paging/sorting. The canonical list-parameter rules and the prohibited aliases (`limit`/`offset`, `per_page`, `sort_dir`, `order_by`, etc.) are defined in `../../docs/docs/architecture/api-contracts.md`.

New endpoint contracts must use `page`, `page_size`, `sort_by`, `order`.
Existing endpoints that use one of these names must be migrated by updating their callers and removing the old names. Compatibility aliases may be added only when explicitly requested by the owner, and only with a documented scope and removal plan.

## Filtering

Filters are query parameters and must use stable snake_case names.

Preferred names:

```txt
client_record_id
business_id
status
date_from
date_to
query
```

Do not mix aliases for the same concept:

```txt
clientId
client_id
client_record
customer_id
```

In this system, when the identifier points to `ClientRecord`, the API field is `client_record_id`.

Filtering for table/list endpoints must happen before pagination and preferably in SQL/backend code.
The frontend must not fetch a broad page and then filter that page in memory for primary resource screens.

## Sorting

Sorting for list endpoints must happen before pagination and preferably in SQL/backend code.

Use:

```txt
sort_by=created_at&order=desc
```

Do not expose free-form column names directly to SQL. Map `sort_by` through an allowlist in the service/repository layer.

## List Response Contract

Every standard list endpoint returns:

```json
{
  "items": [],
  "total": 120,
  "page": 1,
  "page_size": 25
}
```

`total` is the number of records after filters and before pagination.

Domains may add extra fields, such as:

```json
{
  "items": [],
  "total": 120,
  "page": 1,
  "page_size": 25,
  "counters": {}
}
```

but they must not rename the base fields.

## Single Response Contract

Single-resource reads return the DTO directly:

```json
{
  "id": 1,
  "name": "..."
}
```

Do not wrap single resources in inconsistent shapes such as `{ "data": ... }` unless the whole API is migrated to a global envelope.

## Action Response Contract

Business actions should usually return the updated DTO when the frontend needs fresh state.

Example:

```txt
POST /api/v1/binders/{binder_id}/mark-ready-for-handover
```

Response:

```json
{
  "id": 12,
  "status": "ready_for_handover"
}
```

If an action does not naturally return a resource, use a consistent result DTO:

```json
{
  "status": "success",
  "message": "הפעולה בוצעה",
  "data": {}
}
```

## Error Contract

Errors use the project envelope documented in `docs/architecture/api-contracts.md`:

```json
{
  "error": {
    "code": "BINDER.NOT_FOUND",
    "message": "קלסר לא נמצא",
    "details": null,
    "request_id": "..."
  }
}
```

Clients must match on `error.code`, not on Hebrew message text.

## Authorization And Status Codes

Use status codes consistently:

| Status | Meaning |
|--------|---------|
| `401` | user is not authenticated |
| `403` | user is authenticated but not allowed |
| `404` | resource does not exist or is intentionally hidden |
| `409` | business conflict |
| `422` | request validation failed |
| `500` | unexpected server error only |

Do not return `500` for business validation or domain conflicts.

## DTO Boundaries

Routers must return Pydantic response schemas, not raw ORM objects as an implicit contract.

Good:

```python
@router.get("/{client_id}", response_model=ClientResponse)
def get_client(...):
    return service.get_client(client_id)
```

Bad:

```python
return db_client
```

Services may return DTOs or ORM instances depending on existing domain patterns, but the router response model is the public contract.

## Business Action Naming

Use explicit verbs for business transitions:

```txt
POST /binders/{binder_id}/mark-ready-for-handover
POST /binders/{binder_id}/return-to-client
POST /tasks/{task_id}/complete
POST /tasks/{task_id}/cancel
POST /notifications/preview
POST /notifications/send
```

Avoid vague action names:

```txt
POST /binders/{binder_id}/ready
POST /binders/{binder_id}/status
POST /tasks/{task_id}/done
```

## Frontend Expectations

For primary table pages, the frontend should:

- send all filters to the backend
- send `page`, `page_size`, `sort_by`, and `order`
- render pagination from `total`
- avoid in-memory pagination for primary resource screens
- use in-memory slicing only for already-small embedded lists where the API explicitly returns the full set

## Migration Rule

Existing endpoints may deviate from this standard. When touching a list endpoint for feature work, migrate it toward this contract by updating its callers and removing the old names rather than adding another variation.

Do not add compatibility handling to preserve old names by default. Compatibility aliases may be added only when explicitly requested by the owner; when requested, document the reason, scope, and removal plan, and document the target public parameters in the endpoint and frontend API client.
