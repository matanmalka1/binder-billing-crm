# Clients Module

> Last audited: 2026-03-22 (post Client/Business split refactor).

Manages CRM clients at the **identity level only**. Business-level data (type, status, VAT, charges, reports) lives in `app/businesses/`.

## Scope

- CRUD for `clients` (identity: name, ID number, contact, address)
- Filtering + pagination for client lists
- Soft delete with audit fields (`deleted_at`, `deleted_by`, `restored_at`, `restored_by`)
- Role-based API access
- Excel import/export utilities
- Conflict detection for duplicate `id_number`

## Domain Model

`Client` fields:
- `id` (PK)
- `full_name` (required)
- `id_number` (required, unique among active clients)
- `id_number_type` (enum: `individual`, `corporation`, `passport`, `other`; default `individual`)
- `phone`, `email` (optional)
- `address_street`, `address_building_number`, `address_apartment`, `address_city`, `address_zip_code` (optional)
- `notes` (optional)
- `created_by`, `created_at`, `updated_at`
- `deleted_at`, `deleted_by`, `restored_at`, `restored_by` (soft delete)

Implementation references:
- Model: `app/clients/models/client.py`
- Schemas: `app/clients/schemas/client.py`
- Repository: `app/clients/repositories/client_repository.py`
- Service: `app/clients/services/client_service.py`
- API: `app/clients/api/clients.py`
- Excel: `app/clients/api/clients_excel.py`, `app/clients/services/client_excel_service.py`
- Business guards: `app/clients/services/client_lookup.py`

## API

Router prefix is `/api/v1/clients` (mounted in `app/main.py`).

### Create client
- `POST /api/v1/clients`
- Roles: `ADVISOR`, `SECRETARY`
- Body:

```json
{
  "full_name": "ישראל ישראלי",
  "id_number": "123456789",
  "id_number_type": "individual",
  "phone": "050-0000000",
  "email": "client@example.com"
}
```

- ID checksum (Israeli Luhn) is validated only when `id_number_type == individual`.
- Conflict responses:
  - `CLIENT.CONFLICT` (409): active client with same `id_number` exists
  - `CLIENT.DELETED_EXISTS` (409): soft-deleted client with same `id_number` exists

### List clients
- `GET /api/v1/clients`
- Roles: `ADVISOR`, `SECRETARY`
- Query params: `search` (optional), `page` (default `1`), `page_size` (default `20`, max `100`)

### Get client
- `GET /api/v1/clients/{client_id}`
- Roles: `ADVISOR`, `SECRETARY`

### Update client
- `PATCH /api/v1/clients/{client_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Partial update (identity fields only).

### Delete client (soft delete)
- `DELETE /api/v1/clients/{client_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`
- Does not delete the client's businesses — delete them separately via `/businesses/{business_id}`.

### Restore client
- `POST /api/v1/clients/{client_id}/restore`
- Role: `ADVISOR` only
- Raises `CLIENT.CONFLICT` if another active client with the same `id_number` now exists.

### Conflict info
- `GET /api/v1/clients/conflict/{id_number}`
- Roles: `ADVISOR`, `SECRETARY`
- Returns active and deleted clients for a given `id_number`.

### Excel endpoints
- `GET /api/v1/clients/export` — export all clients as Excel
- `GET /api/v1/clients/template` — download import template
- `POST /api/v1/clients/import` — bulk create from Excel (ADVISOR only, max 10MB)

## Cross-Domain Integration

- `businesses`: client identity is the parent of one or more `Business` records.
- `binders`: binders belong to clients via `client_id`.
- `status card`, `binders list`, `tax profile`: served under `/api/v1/businesses/{business_id}/` — see `app/businesses/`.
- `business guards`: `assert_business_allows_create` and `assert_business_not_closed` are defined in `app/clients/services/client_lookup.py` and used across multiple domains (binders, charge, vat_reports, annual_reports, etc.).

## Error Codes

- `CLIENT.NOT_FOUND`
- `CLIENT.CONFLICT`
- `CLIENT.DELETED_EXISTS`
- `CLIENT.NOT_DELETED`

## Tests

```
tests/clients/api/test_clients.py
tests/clients/api/test_clients_binders.py
tests/clients/api/test_clients_excel.py
tests/clients/service/test_client_service_list_all_clients.py
tests/clients/repository/test_client_repository.py
```

Run only this domain:

```bash
JWT_SECRET=test-secret pytest -q tests/clients/
```
