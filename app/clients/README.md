# Clients Module

> Last audited: 2026-04-16

Manages CRM clients at the identity level only. Business-level state (status, tax profile, VAT/report workflows, etc.) is handled under `app/businesses/` and related domains.

## Scope

- CRUD for `clients` identity data
- Search + pagination for active clients
- Soft delete + restore flow with audit columns
- Conflict detection by `id_number` (active vs soft-deleted records)
- Excel export/template/import endpoints

Comments:
- This module should stay identity-only. If a field is business-process related, it belongs in `businesses` (or a dedicated domain), not here.
- Soft delete is part of the domain contract. Avoid hard deletes unless there is a migration/maintenance requirement.

## Implementation Map

- Model: `app/clients/models/client.py`
- Schemas: `app/clients/schemas/client.py`
- Repository: `app/clients/repositories/client_repository.py`
- Service: `app/clients/services/client_service.py`
- Create-client orchestration: `app/clients/services/create_client_service.py`
- Query service: `app/clients/services/client_query_service.py`
- API: `app/clients/api/clients.py`
- Enrichment (active binder number): `app/clients/services/client_enrichment_service.py`
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

Comments:
- The 9-digit rule is currently global across ID types by design in `ClientCreateRequest`; changing this affects API behavior and tests.

## API

Routers are mounted with `/api/v1` in `app/router_registry.py`, so clients endpoints are under `/api/v1/clients`.

- `POST /api/v1/clients` (`ADVISOR` only) - create client and first business together
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

Comments:
- Import is partial-success by design: valid rows are created, invalid rows are returned in the `errors` array.
- Import requires `Full Name`, `Business Name`, and `ID Number`; valid rows create a client and first business together.
- Identity-only client creation is not exposed through the API.

## Error Codes

- `CLIENT.NOT_FOUND`
- `CLIENT.CONFLICT`
- `CLIENT.DELETED_EXISTS`
- `CLIENT.NOT_DELETED`

## Cross-Domain Notes

- A client can have multiple businesses (`app/businesses/`).
- `GET /api/v1/clients/{client_id}/binders` — served by `app/binders/api/client_binders_router.py`.
- `GET /api/v1/clients/{client_id}/status-card` — served by `app/businesses/api/client_status_card_router.py`.
- Initial binder creation on client creation is handled by `app/binders/services/client_onboarding_service.py`.
- Obligation generation (tax deadlines + annual reports) on client create/update is handled by `app/actions/obligation_orchestrator.py`.
- Business guard helpers (`assert_business_allows_create`, `assert_business_not_closed`) are in `app/businesses/services/business_guards.py`.

Comments:
- If client deletion/restoration rules change, check downstream flows that resolve binders/status via `client_id`.

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

Comments:
- Run this suite after changing schemas, conflict logic, or Excel import/export behavior.
