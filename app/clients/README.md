# Clients Module

> Last audited: 2026-04-21

Manages CRM clients as a two-layer identity model: `LegalEntity` (tax/legal identity, globally unique) and `ClientRecord` (office CRM anchor, one active record per legal entity). Business-level state (binders, VAT/report workflows, etc.) is handled under `app/businesses/` and related domains.

## Scope

- CRUD for `ClientRecord` and underlying `LegalEntity`
- Optional `Person` + `PersonLegalEntityLink` for natural-person associations
- Search + pagination + status filtering for clients
- Soft delete + restore flow with audit columns
- Conflict detection by `id_number`
- Excel export/template/import endpoints
- Impact preview for client creation (projected obligations)

Comments:
- This module is identity-only. Business-process fields belong in `businesses` or a dedicated domain.
- Soft delete is part of the domain contract. Avoid hard deletes unless there is a migration/maintenance requirement.

## Implementation Map

- Models: `app/clients/models/legal_entity.py`, `app/clients/models/client_record.py`, `app/clients/models/person.py`, `app/clients/models/person_legal_entity_link.py`
- Schemas: `app/clients/schemas/client.py`, `app/clients/schemas/client_record_response.py`, `app/clients/schemas/impact.py`
- Repositories: `app/clients/repositories/client_record_repository.py`, `app/clients/repositories/client_record_read_repository.py`, `app/clients/repositories/legal_entity_repository.py`, `app/clients/repositories/person_repository.py`, `app/clients/repositories/client_repository.py`
- Services: `app/clients/services/client_service.py`, `app/clients/services/create_client_service.py`, `app/clients/services/client_creation_service.py`, `app/clients/services/client_query_service.py`, `app/clients/services/client_enrichment_service.py`, `app/clients/services/client_update_service.py`, `app/clients/services/client_lifecycle_service.py`, `app/clients/services/impact_preview_service.py`
- Guards: `app/clients/guards/client_record_guards.py`
- API: `app/clients/api/clients.py`, `app/clients/api/clients_excel.py`
- Enums: `app/clients/enums.py` (`ClientStatus`); entity/VAT/ID-type enums live in `app/common/enums.py`

## Domain Model

### LegalEntity

The stable tax/legal identity. Globally unique by `(id_number_type, id_number)`.

Key fields:
- `id` (PK)
- `id_number`, `id_number_type` (`IdNumberType` enum)
- `official_name`
- `entity_type` (`EntityType`)
- `vat_reporting_frequency` (`VatType`)
- `vat_exempt_ceiling`, `advance_rate`, `advance_rate_updated_at`
- `created_at`, `updated_at`

Indexes/uniqueness:
- `UniqueConstraint("id_number_type", "id_number")` — global, not soft-delete-aware
- Index on `official_name`

### ClientRecord

Office CRM record anchored to a `LegalEntity`. One active record per entity (soft-delete-aware unique index).

Key fields:
- `id` (PK) — this is `client_record_id` across the codebase
- `legal_entity_id` (FK → `legal_entities.id`)
- `office_client_number` (optional, unique among active records)
- `accountant_id`, `status` (`ClientStatus`: `active`, `frozen`, `closed`), `notes`
- Audit: `created_by`, `created_at`, `updated_at`
- Soft-delete: `deleted_at`, `deleted_by`, `restored_at`, `restored_by`

### Person / PersonLegalEntityLink

Optional natural-person identity linked to a `LegalEntity`. Used for sole traders and similar.

## API

Routers mounted at `/api/v1/clients` via `app/router_registry.py`.

- `POST /api/v1/clients/preview-impact` (`ADVISOR`) — dry-run: returns projected obligations without writing
- `POST /api/v1/clients` (`ADVISOR`) — create `LegalEntity` + `ClientRecord` + first business in one request
- `GET /api/v1/clients` (`ADVISOR`, `SECRETARY`) — list clients (`search`, `status`, `sort_by`, `sort_order`, `page`, `page_size<=100`)
- `GET /api/v1/clients/{client_id}` (`ADVISOR`, `SECRETARY`) — get by `ClientRecord.id`
- `PATCH /api/v1/clients/{client_id}` (`ADVISOR`, `SECRETARY`) — partial update
- `DELETE /api/v1/clients/{client_id}` (`ADVISOR`) — soft delete
- `POST /api/v1/clients/{client_id}/restore` (`ADVISOR`) — restore soft-deleted client
- `GET /api/v1/clients/conflict/{id_number}` (`ADVISOR`, `SECRETARY`) — active/deleted conflict info

Excel endpoints:
- `GET /api/v1/clients/export` (`ADVISOR`, `SECRETARY`)
- `GET /api/v1/clients/template` (`ADVISOR`, `SECRETARY`)
- `POST /api/v1/clients/import` (`ADVISOR`, max upload 10MB)

Comments:
- `client_id` in all route params refers to `ClientRecord.id`, not `LegalEntity.id`.
- Import is partial-success: valid rows are created, invalid rows returned in the `errors` array.
- Import requires `X-Idempotency-Key`.
- Import requires `Full Name`, `Business Name`, and `ID Number`; valid rows create a client and first business together.
- Identity-only client creation (no business) is not exposed through the API.

## Error Codes

- `CLIENT.NOT_FOUND`
- `CLIENT.CONFLICT`
- `CLIENT.DELETED_EXISTS`
- `CLIENT.NOT_DELETED`

## Cross-Domain Notes

- A client can have multiple businesses (`app/businesses/`).
- `GET /api/v1/clients/{client_id}/binders` — served by `app/binders/api/client_binders_router.py`.
- `GET /api/v1/clients/{client_id}/status-card` — served by `app/businesses/api/client_status_card_router.py`.
- Initial binder creation on client creation: `app/binders/services/client_onboarding_service.py`.
- Obligation generation (tax deadlines + annual reports) on client create/update: `app/actions/obligation_orchestrator.py`.
- Business guard helpers: `app/businesses/services/business_guards.py`.

Comments:
- If client deletion/restoration rules change, check downstream flows that resolve binders/status via `client_record_id`.

## Tests

- `tests/clients/api/test_clients.py`
- `tests/clients/api/test_clients_mutations_additional.py`
- `tests/clients/api/test_clients_excel.py`
- `tests/clients/api/test_onboarding_layer1.py`
- `tests/clients/service/test_client_service_mutations.py`
- `tests/clients/service/test_client_service_list_all_clients.py`
- `tests/clients/service/test_client_excel_service.py`
- `tests/clients/service/test_client_schema_and_model.py`
- `tests/clients/service/test_client_creation_service.py`
- `tests/clients/service/test_entity_type_change_guard.py`
- `tests/clients/repository/test_client_repository.py`
- `tests/clients/repository/test_client_record_repository.py`

Run clients tests:

```bash
JWT_SECRET=test-secret pytest -q tests/clients
```

Comments:
- Run after changing schemas, conflict logic, entity model, or Excel import/export behavior.
