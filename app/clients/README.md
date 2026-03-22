# Clients Module

> Last audited: 2026-03-22

Manages CRM clients at the identity level only. Business-level state (status, tax profile, VAT/report workflows, etc.) is handled under `app/businesses/` and related domains.

## Scope

- CRUD for `clients` identity data
- Search + pagination for active clients
- Soft delete + restore flow with audit columns
- Conflict detection by `id_number` (active vs soft-deleted records)
- Excel export/template/import endpoints

## Implementation Map

- Model: `app/clients/models/client.py`
- Schemas: `app/clients/schemas/client.py`
- Repository: `app/clients/repositories/client_repository.py`
- Service: `app/clients/services/client_service.py`
- API: `app/clients/api/clients.py`
- Excel API/service: `app/clients/api/clients_excel.py`, `app/clients/services/client_excel_service.py`

## Domain Model

Primary `Client` fields:

- `id` (PK)
- `full_name` (required)
- `id_number` (required)
- `id_number_type` (`individual`, `corporation`, `passport`, `other`; default `individual`)
- Optional contact/address fields: `phone`, `email`, `address_*`
- `notes`
- Audit fields: `created_by`, `created_at`, `updated_at`
- Soft-delete fields: `deleted_at`, `deleted_by`, `restored_at`, `restored_by`

Indexes/uniqueness:

- Partial unique index on `id_number` for active (non-deleted) clients only
- Index on `full_name`

Validation highlights:

- `id_number` must be exactly 9 digits for all ID types (schema-level validation)
- Israeli checksum validation is applied only when `id_number_type == individual`

## API

Routers are mounted with `/api/v1` in `app/router_registry.py`, so clients endpoints are under `/api/v1/clients`.

- `POST /api/v1/clients` (`ADVISOR`, `SECRETARY`) - create client
- `GET /api/v1/clients` (`ADVISOR`, `SECRETARY`) - list clients (`search`, `page`, `page_size<=100`)
- `GET /api/v1/clients/{client_id}` (`ADVISOR`, `SECRETARY`) - get by id
- `PATCH /api/v1/clients/{client_id}` (`ADVISOR`, `SECRETARY`) - partial update
- `DELETE /api/v1/clients/{client_id}` (`ADVISOR` only) - soft delete
- `POST /api/v1/clients/{client_id}/restore` (`ADVISOR` only) - restore soft-deleted client
- `GET /api/v1/clients/conflict/{id_number}` (`ADVISOR`, `SECRETARY`) - active/deleted conflict info

Excel endpoints:

- `GET /api/v1/clients/export` (`ADVISOR`, `SECRETARY`)
- `GET /api/v1/clients/template` (`ADVISOR`, `SECRETARY`)
- `POST /api/v1/clients/import` (`ADVISOR` only, max upload 10MB)

## Error Codes

- `CLIENT.NOT_FOUND`
- `CLIENT.CONFLICT`
- `CLIENT.DELETED_EXISTS`
- `CLIENT.NOT_DELETED`

## Cross-Domain Notes

- A client can have multiple businesses (`app/businesses/`).
- Binders are client-scoped (`client_id`) and are reused in business status-card aggregation.
- Business guard helpers (`assert_business_allows_create`, `assert_business_not_closed`) are defined in `app/businesses/services/business_guards.py` and used by several domains.

## Tests

Current clients domain test files:

- `tests/clients/api/test_clients.py`
- `tests/clients/api/test_clients_mutations_additional.py`
- `tests/clients/api/test_clients_excel.py`
- `tests/clients/service/test_client_service_mutations.py`
- `tests/clients/service/test_client_service_list_all_clients.py`
- `tests/clients/service/test_client_excel_service.py`
- `tests/clients/service/test_client_schema_and_model.py`
- `tests/clients/repository/test_client_repository.py`

Run clients tests:

```bash
pytest -q tests/clients
```
