# Binders Module

> Last audited: 2026-03-22 (domain-by-domain backend sync).

Manages physical binder lifecycle in the CRM: intake (find-or-create), operational tracking, ready-for-pickup, return, audit history, and list views enriched with derived operational metadata.

## Scope

This module provides:
- Binder intake — find active binder by number or create new one, record material intake event
- Lifecycle transitions (`in_office -> ready_for_pickup -> returned`)
- `returned` is terminal in the current implementation; no reopen action/API exists
- Active/open binder listing with filters, sort, and pagination
- Binder history/audit trail (`binder_status_logs`)
- Business-scoped binder listing (`/businesses/{business_id}/binders`)
- Soft delete with audit fields (`deleted_at`, `deleted_by`)
- Derived UX fields (`days_in_office`, `available_actions`)

## Domain Model

### `Binder` (`app/binders/models/binder.py`)

Primary fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required) — binders belong to the client, not a specific business
- `binder_number` (required) — globally unique label on the physical binder
- `period_start` (date, required) — start of the binder's reporting period
- `period_end` (date, optional) — null means the binder is still active
- `status` (enum, required, default `in_office`)
- `returned_at` (date, optional)
- `pickup_person_name` (optional) — who collected the binder
- `notes` (optional)
- `created_at`
- `created_by` (FK -> `users.id`, required)
- `deleted_at`, `deleted_by` (soft delete)

Status enum values:
- `in_office`
- `ready_for_pickup`
- `returned`

Indexes and uniqueness:
- `idx_binder_client` on `client_id`
- `idx_binder_status` on `status`
- `idx_binder_period_start` on `period_start`
- Partial unique index `idx_active_binder_unique` on `binder_number` for non-returned, non-deleted binders

### `BinderIntake` (`app/binders/models/binder_intake.py`)

Records a single material intake event — every time a client brings materials to the office.

Fields:
- `id` (PK)
- `binder_id` (FK -> `binders.id`, required)
- `received_at` (date, required)
- `received_by` (FK -> `users.id`, required)
- `notes` (optional)
- `created_at`

### `BinderIntakeMaterial` (`app/binders/models/binder_intake_material.py`)

One item within an intake event — a specific material type for a specific business.

Fields:
- `id` (PK)
- `intake_id` (FK -> `binder_intakes.id`, required)
- `business_id` (FK -> `businesses.id`, optional) — null means all businesses under the client
- `material_type` (enum, required)
- `annual_report_id` (FK -> `annual_reports.id`, optional)
- `description` (optional)
- `created_at`

Material type enum values:
- `vat`
- `income_tax`
- `annual_report`
- `salary`
- `bookkeeping`
- `national_insurance`
- `capital_declaration`
- `pension_and_insurance`
- `corporate_docs`
- `tax_assessment`
- `other`

### `BinderStatusLog` (`app/binders/models/binder_status_log.py`)

Audit log fields:
- `id` (PK)
- `binder_id` (FK -> `binders.id`)
- `old_status`, `new_status`
- `changed_by` (FK -> `users.id`)
- `changed_at`
- `notes`

## API

Routers are mounted with `/api/v1` in `app/main.py`.

### Core binder routes (`app/binders/api/binders_receive_return.py`, `app/binders/api/binders_list_get.py`)

Base prefix: `/api/v1/binders`

Role access:
- Default: `ADVISOR`, `SECRETARY`
- Delete only: `ADVISOR`

#### Receive binder
- `POST /api/v1/binders/receive`
- Find-or-create: if `binder_number` matches an active binder for this client, adds an intake to it. Otherwise creates a new binder.
- Request body (`BinderReceiveRequest`):

```json
{
  "client_id": 123,
  "binder_number": "BND-2026-001",
  "period_start": "2026-01-01",
  "received_at": "2026-03-16",
  "received_by": 7,
  "notes": "Optional",
  "materials": [
    {
      "material_type": "vat",
      "business_id": 45,
      "description": "January invoices"
    }
  ]
}
```

- Response: `BinderReceiveResult`
  - `binder` — enriched `BinderResponse`
  - `intake` — `BinderIntakeResponse` with material list
  - `is_new_binder` — `true` if a new binder was created
- Behavior: creates or reuses binder, records intake + materials, writes status log (`null -> in_office`) on new binder, triggers binder-received notification on new binder only

#### Mark ready for pickup
- `POST /api/v1/binders/{binder_id}/ready`
- Valid only from `in_office`
- Response: `BinderResponse`
- Behavior: status update + status log + ready notification

#### Return binder
- `POST /api/v1/binders/{binder_id}/return`
- Body is optional (`BinderReturnRequest`)
- If body is empty:
  - `pickup_person_name` defaults to authenticated user `full_name`
  - `returned_by` defaults to authenticated user `id`
- Valid only from `ready_for_pickup`
- Behavior: sets `status=returned`, `returned_at=today`, `returned_by`, `pickup_person_name`, appends status log

#### List active binders
- `GET /api/v1/binders`
- Returns active binders (`status != returned`) with pagination
- Response also includes `counters` for list pills across all non-deleted binders matching the
  current non-status filters:
  - `total`
  - `in_office`
  - `ready_for_pickup`
  - `returned`
- Query params:
  - `status`
  - `client_id`
  - `query` (matches client name or binder number)
  - `client_name`
  - `binder_number`
  - `year`
  - `page` (default `1`)
  - `page_size` (default `20`, max `100`)
  - `sort_by` (`period_start`, `days_in_office`, `status`, `client_name`)
  - `sort_dir` (`asc`, `desc`, defaults to `desc`)

#### Get binder by id
- `GET /api/v1/binders/{binder_id}`
- Response: enriched `BinderResponse`

#### Soft delete binder
- `DELETE /api/v1/binders/{binder_id}`
- Role: `ADVISOR`
- Response: `204 No Content`
- Behavior: sets `status=returned` (if not already), `deleted_at`, `deleted_by`

### Operations routes (`app/binders/api/binders_operations.py`)

Base prefix: `/api/v1/binders`

#### List open binders
- `GET /api/v1/binders/open`
- Returns binders where `status != returned`
- Response model: `BinderListResponseExtended`

### History routes (`app/binders/api/binders_history.py`)

Base prefix: `/api/v1/binders`

#### Binder audit history
- `GET /api/v1/binders/{binder_id}/history`
- Response model: `BinderHistoryResponse`

#### Binder intake history
- `GET /api/v1/binders/{binder_id}/intakes`
- Response model: `BinderIntakeListResponse`
- Returns all intake events for the binder with `received_by_name` enrichment and material items

### Business-scoped binders (cross-domain route)

Implemented in `app/businesses/api/business_binders_router.py`.
Resolves `business.client_id` and delegates to `BinderOperationsService`.

- `GET /api/v1/businesses/{business_id}/binders`
- Returns all binders for the client that owns the business (paginated)

## Lifecycle and Rules

Transition rules (`app/binders/services/binder_helpers.py`):
- `in_office -> ready_for_pickup` only
- `ready_for_pickup -> in_office` only (via `revert-ready`)
- `ready_for_pickup -> returned` only
- `returned` is terminal; there is currently no `returned -> in_office` transition
- Return requires non-empty pickup person name

Intake rules (`app/binders/services/binder_intake_service.py`):
- If an active binder with the same `binder_number` exists for this client, the intake is appended to it
- If the binder belongs to a different client, `BINDER.CLIENT_MISMATCH` is raised
- If no active binder exists, a new one is created with status `in_office`
- Notification is sent only on new binder creation

Derived fields (`app/binders/services/binder_list_service.py`):
- `days_in_office`: `today - period_start`
- `available_actions`: generated action contracts for frontend execution

## Error Codes

Common domain errors surfaced from binder services:
- `BINDER.CONFLICT` (active binder number already exists for a different client — use intake flow)
- `BINDER.CLIENT_MISMATCH` (binder_number belongs to a different client)
- `BINDER.NOT_FOUND`
- `BINDER.INVALID_STATUS`
- `BINDER.MISSING_PICKUP_PERSON`
- `CLIENT.NOT_FOUND` (on receive if client does not exist)

Errors follow the global envelope from `app/core/exceptions.py` with:
- `detail`
- `error`
- `error_meta`

## Implementation Map

- API:
  - `app/binders/api/binders.py`
  - `app/binders/api/binders_receive_return.py`
  - `app/binders/api/binders_list_get.py`
  - `app/binders/api/binders_operations.py`
  - `app/binders/api/binders_history.py`
- Schemas:
  - `app/binders/schemas/binder.py`
  - `app/binders/schemas/binder_extended.py`
- Services:
  - `app/binders/services/binder_service.py`
  - `app/binders/services/binder_list_service.py`
  - `app/binders/services/binder_operations_service.py`
  - `app/binders/services/binder_history_service.py`
  - `app/binders/services/binder_intake_service.py`
  - `app/binders/services/signals_service.py`
- Repositories:
  - `app/binders/repositories/binder_repository.py`
  - `app/binders/repositories/binder_repository_extensions.py`
  - `app/binders/repositories/binder_status_log_repository.py`
  - `app/binders/repositories/binder_intake_repository.py`
  - `app/binders/repositories/binder_intake_material_repository.py`
- Models:
  - `app/binders/models/binder.py`
  - `app/binders/models/binder_status_log.py`
  - `app/binders/models/binder_intake.py`
  - `app/binders/models/binder_intake_material.py`

## Tests

Domain tests:
- `tests/binders/api/test_binders.py`
- `tests/binders/api/test_binder_history.py`
- `tests/binders/service/test_binder_service_basic.py`
- `tests/binders/service/test_binder_operations_service.py`
- `tests/binders/service/test_operational_signals.py`
- `tests/binders/repository/test_binder_repository.py`
- `tests/binders/repository/test_binder_repository_extensions.py`

Cross-domain binders API test:
- `tests/businesses/api/test_business_binders.py`

Run binder-focused tests:

```bash
pytest tests/binders tests/businesses/api/test_business_binders.py -q
```
