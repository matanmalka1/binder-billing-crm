# Clients Module

Manages CRM clients (identity, lifecycle status, contact details, address, and related client-level views) and exposes core client APIs consumed by other domains.

## Scope

This module provides:
- CRUD for `clients`
- Filtering + pagination for client lists
- Soft delete with audit fields (`deleted_at`, `deleted_by`)
- Role-based API access
- Client status-card endpoint (aggregated cross-domain view)
- Client binders listing endpoint
- Client Excel import/export utilities
- Client tax-profile get/update endpoints

## Domain Model

`Client` fields:
- `id` (PK)
- `full_name` (required)
- `id_number` (unique, required)
- `client_type` (enum, required)
- `status` (enum, default `active`)
- `primary_binder_number` (optional, unique)
- `phone`, `email`, `notes` (optional)
- Legacy `address` (optional; kept for backward compatibility)
- Structured address fields:
  - `address_street`
  - `address_building_number`
  - `address_apartment`
  - `address_city`
  - `address_zip_code`
- `opened_at` (required)
- `closed_at` (optional)
- `created_by`, `updated_at`
- `deleted_at`, `deleted_by` (for soft delete)

Client type enum values:
- `osek_patur`
- `osek_murshe`
- `company`
- `employee`

Client status enum values:
- `active`
- `frozen`
- `closed`

Implementation references:
- Model: `app/clients/models/client.py`
- Schemas: `app/clients/schemas/client.py`
- Repository: `app/clients/repositories/client_repository.py`
- Service: `app/clients/services/client_service.py`
- API: `app/clients/api/clients.py`

## API

Router prefix is `/api/v1/clients` (mounted in `app/main.py`).

### Create client
- `POST /api/v1/clients`
- Roles: `ADVISOR`, `SECRETARY`
- Body:

```json
{
  "full_name": "Example Client",
  "id_number": "123456789",
  "client_type": "company",
  "phone": "050-0000000",
  "email": "client@example.com",
  "opened_at": "2026-03-16"
}
```

### List clients
- `GET /api/v1/clients`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `status` (optional)
  - `has_signals` (optional boolean)
  - `search` (optional)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

### Get client
- `GET /api/v1/clients/{client_id}`
- Roles: `ADVISOR`, `SECRETARY`

### Update client
- `PATCH /api/v1/clients/{client_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Partial update supported.

### Bulk client status action
- `POST /api/v1/clients/bulk-action`
- Role: `ADVISOR` only
- Applies one action to multiple clients in a single request.
- Supported actions:
  - `freeze`
  - `close`
  - `activate`

### Delete client (soft delete)
- `DELETE /api/v1/clients/{client_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

### Client status card
- `GET /api/v1/clients/{client_id}/status-card`
- Roles: `ADVISOR`, `SECRETARY`
- Returns aggregated client operational status (VAT, annual report, charges, advances, binders, documents).

### Client binders list
- `GET /api/v1/clients/{client_id}/binders`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

### Tax profile get/update
- `GET /api/v1/clients/{client_id}/tax-profile`
- `PATCH /api/v1/clients/{client_id}/tax-profile`
- Roles: `ADVISOR`, `SECRETARY`

### Excel endpoints
- `GET /api/v1/clients/export`
- `GET /api/v1/clients/template`
- `POST /api/v1/clients/import`
- Roles: protected by the `/clients` router role dependency (`ADVISOR`, `SECRETARY`)

## Behavior Notes

- Creating a client validates required fields and uniqueness constraints (for example `id_number`).
- `available_actions` is attached to client responses based on client status and user role (via `app/actions/action_contracts.py`).
- Bulk action endpoint applies advisor-only lifecycle transitions to multiple clients and returns per-id success/failure buckets.
- List and get operations exclude soft-deleted clients.
- Client delete does not remove rows; it sets `deleted_at` + `deleted_by`.
- `/clients/{client_id}/binders` returns `404` when the client does not exist.
- Excel import:
  - Max upload size is 10MB.
  - Empty rows are skipped.
  - Per-row errors are returned without failing the entire import.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `CLIENT.NOT_FOUND`
- `CLIENT.CONFLICT`

Additional route-specific HTTP errors are also used (for example validation or missing resource cases).

## Cross-Domain Integration

- `binders`: `/clients/{client_id}/binders` is served through binders operational services.
- `status card`: aggregates data from VAT, annual reports, charges, advance payments, binders, and documents.
- `tax profile`: backed by `client_tax_profile` domain model and repository.
- `actions`: client responses include executable action contracts from `app/actions/action_contracts.py`.

## Tests

Clients test suites:
- `tests/clients/api/test_clients.py`
- `tests/clients/api/test_clients_binders.py`
- `tests/clients/api/test_client_status_card.py`
- `tests/clients/api/test_client_tax_profile.py`
- `tests/clients/api/test_clients_excel.py`
- `tests/clients/service/test_client_service_list_all_clients.py`
- `tests/clients/service/test_client_tax_profile_service.py`
- `tests/clients/repository/test_client_repository.py`
- `tests/clients/repository/test_client_tax_profile_repository.py`

Run only this domain:

```bash
pytest tests/clients -q
```
