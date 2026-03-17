# Binders Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Manages physical binder lifecycle in the CRM: intake, operational tracking, ready-for-pickup, return, audit history, and list views enriched with derived operational metadata.

## Scope

This module provides:
- Binder intake (`in_office`)
- Lifecycle transitions (`in_office -> ready_for_pickup -> returned`)
- Active/open binder listing with filters, sort, and pagination
- Binder history/audit trail (`binder_status_logs`)
- Client-scoped binder listing (`/clients/{client_id}/binders`)
- Soft delete with audit fields (`deleted_at`, `deleted_by`)
- Derived UX fields (`days_in_office`, `work_state`, `signals`, `available_actions`)

## Domain Model

### `Binder` (`app/binders/models/binder.py`)

Primary fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `binder_number` (required)
- `binder_type` (enum, required)
- `received_at` (date, required)
- `status` (enum, required, default `in_office`)
- `received_by` (FK -> `users.id`, required)
- `returned_at`, `returned_by`, `pickup_person_name` (return metadata)
- `annual_report_id` (optional FK -> `annual_reports.id`)
- `notes` (optional)
- `created_at`
- `deleted_at`, `deleted_by` (soft delete)

Status enum values:
- `in_office`
- `ready_for_pickup`
- `returned`

Type enum values:
- `vat`
- `income_tax`
- `national_insurance`
- `capital_declaration`
- `annual_report`
- `salary`
- `bookkeeping`
- `other`

Indexes and uniqueness:
- `idx_binder_status` on `status`
- `idx_binder_received_at` on `received_at`
- Partial unique index `idx_active_binder_unique` on `binder_number` for non-returned binders

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
- Request body (`BinderReceiveRequest`):

```json
{
  "client_id": 123,
  "binder_number": "BND-2026-001",
  "binder_type": "other",
  "received_at": "2026-03-16",
  "received_by": 7,
  "notes": "Optional"
}
```

- Response: `BinderResponse` (includes derived fields)
- Behavior: creates binder, writes initial status log (`null -> in_office`), triggers binder-received notification

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
- Query params:
  - `status`
  - `client_id`
  - `work_state`
  - `query` (matches client name or binder number)
  - `client_name`
  - `binder_number`
  - `year`
  - `page` (default `1`)
  - `page_size` (default `20`, max `100`)
  - `sort_by` (`received_at`, `days_in_office`, `status`, `client_name`)
  - `sort_dir` (`asc`, `desc`, defaults to `desc`)

#### Get binder by id
- `GET /api/v1/binders/{binder_id}`
- Response: enriched `BinderResponse`

#### Soft delete binder
- `DELETE /api/v1/binders/{binder_id}`
- Role: `ADVISOR`
- Response: `204 No Content`
- Behavior: sets `deleted_at` + `deleted_by`

### Operations routes (`app/binders/api/binders_operations.py`)

Base prefix: `/api/v1/binders`

#### List open binders
- `GET /api/v1/binders/open`
- Returns binders where `status != returned`
- Response model: `BinderListResponseExtended` (`work_state`, `signals` included)

### History routes (`app/binders/api/binders_history.py`)

Base prefix: `/api/v1/binders`

#### Binder audit history
- `GET /api/v1/binders/{binder_id}/history`
- Response model: `BinderHistoryResponse`

#### Binder intake history
- `GET /api/v1/binders/{binder_id}/intakes`
- Response model: `BinderIntakeListResponse`
- Returns intake rows with `received_by_name` enrichment

### Client-scoped binders (cross-domain route)

Implemented in `app/clients/api/clients_binders.py` using binders services.

- `GET /api/v1/clients/{client_id}/binders`
- Returns all binders for a client (paginated), enriched with `work_state` and `signals`

## Lifecycle and Rules

Transition rules (`app/binders/services/binder_helpers.py`):
- `in_office -> ready_for_pickup` only
- `ready_for_pickup -> returned` only
- Return requires non-empty pickup person name

Derived fields (`app/binders/services/binder_list_service.py`):
- `days_in_office`: `today - received_at`
- `work_state`: derived by `WorkStateService`
- `signals`: derived by `SignalsService`
- `available_actions`: generated action contracts for frontend execution

Work state (`app/binders/services/work_state_service.py`):
- `completed`: binder status is `returned`
- `in_progress`: ready-for-pickup, or received in last 14 days, or recent notification activity
- `waiting_for_work`: older than threshold and no recent activity

Signals (`app/binders/services/signals_service.py`):
- Binder-level signals currently include:
  - `ready_for_pickup`
  - `idle_binder`

## Error Codes

Common domain errors surfaced from binder services:
- `BINDER.CONFLICT` (active binder number already exists)
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
  - `app/binders/services/work_state_service.py`
  - `app/binders/services/signals_service.py`
- Repositories:
  - `app/binders/repositories/binder_repository.py`
  - `app/binders/repositories/binder_repository_extensions.py`
  - `app/binders/repositories/binder_status_log_repository.py`
- Models:
  - `app/binders/models/binder.py`
  - `app/binders/models/binder_status_log.py`

## Tests

Domain tests:
- `tests/binders/api/test_binders.py`
- `tests/binders/api/test_binder_history.py`
- `tests/binders/service/test_binder_service_basic.py`
- `tests/binders/service/test_binder_operations_service.py`
- `tests/binders/service/test_work_state.py`
- `tests/binders/service/test_signals.py`
- `tests/binders/service/test_operational_signals.py`
- `tests/binders/service/test_signals_service_client_signals.py`
- `tests/binders/repository/test_binder_repository.py`
- `tests/binders/repository/test_binder_repository_extensions.py`

Cross-domain binders API test:
- `tests/clients/api/test_clients_binders.py`

Run binder-focused tests:

```bash
pytest tests/binders tests/clients/api/test_clients_binders.py -q
```
