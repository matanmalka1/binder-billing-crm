# Businesses Module

> Last audited: 2026-03-22 (domain-by-domain backend sync).

Manages business entities under clients — business type, operational status, tax profile, lifecycle actions, and the aggregated status-card view. A client can hold multiple businesses.

## Scope

This module provides:
- CRUD for `businesses` under a client
- Business status lifecycle (active → frozen → closed) with role enforcement
- Soft delete and restore with audit fields
- Bulk status actions (freeze / close / activate) across multiple businesses
- Business tax profile get/update (VAT type, advance rate, fiscal year)
- Aggregated business status card (VAT, annual report, charges, advances, binders, documents)
- `has_signals` filtering with in-memory safety ceiling
- Business-scoped binder listing (delegates to binders domain)
- `available_actions` attached to every business response

## Domain Model

### `Business` (`app/businesses/models/business.py`)

Primary fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required) — the person who owns this business
- `business_name` (optional) — null means the sole proprietor operates under their personal name
- `business_type` (enum, required)
- `tax_id_number` (optional, unique among active non-deleted businesses)
- `status` (enum, required, default `active`)
- `opened_at` (date, required)
- `closed_at` (date, optional)
- `phone`, `email` (business-specific contact details; properties fall back to client when null)
- `assigned_to` (FK -> `users.id`, optional)
- `notes` (optional)
- `created_by` (FK -> `users.id`, optional)
- `created_at`, `updated_at`
- `deleted_at`, `deleted_by`, `restored_at`, `restored_by` (soft delete / restore)

Computed properties:
- `full_name` — returns `business_name` if set, otherwise `client.full_name`
- `contact_phone` — `phone` with fallback to `client.phone`
- `contact_email` — `email` with fallback to `client.email`

Business type enum values:
- `osek_patur` — exempt dealer
- `osek_murshe` — authorized dealer
- `company` — limited company
- `employee`

Business status enum values:
- `active`
- `frozen`
- `closed`

Indexes and uniqueness:
- `ix_business_client_id` on `client_id`
- `ix_business_status` on `status`
- `ix_business_assigned` on `assigned_to`
- Partial unique index `ix_business_tax_id` on `tax_id_number` for non-deleted businesses
- Partial unique index `ix_business_client_name_active` on `(client_id, business_name)` for non-null, non-deleted businesses

### `BusinessTaxProfile` (`app/businesses/models/business_tax_profile.py`)

One-to-one with `Business`. Created on first update (upsert).

Fields:
- `id` (PK)
- `business_id` (FK -> `businesses.id`, unique, required)
- `vat_type` (enum, optional)
- `vat_start_date` (date, optional)
- `vat_exempt_ceiling` (Numeric, optional) — current statutory ceiling for OSEK_PATUR
- `accountant_name` (optional)
- `advance_rate` (Numeric 5,2, optional) — percentage used to calculate monthly advance payments
- `advance_rate_updated_at` (date, optional)
- `fiscal_year_start_month` (integer, default `1`)
- `created_at`, `updated_at`

VAT type enum values:
- `monthly`
- `bimonthly`
- `exempt`

Implementation references:
- Models: `app/businesses/models/business.py`, `app/businesses/models/business_tax_profile.py`
- Schemas: `app/businesses/schemas/business_schemas.py`, `app/businesses/schemas/business_tax_profile_schemas.py`
- Repositories: `app/businesses/repositories/business_repository.py`, `app/businesses/repositories/business_tax_profile_repository.py`
- Services: `app/businesses/services/business_service.py`, `app/businesses/services/business_tax_profile_service.py`, `app/businesses/services/business_lookup.py`
- APIs: `app/businesses/api/businesses.py`, `app/businesses/api/business_tax_profile_router.py`, `app/businesses/api/business_status_card_router.py`, `app/businesses/api/business_binders_router.py`

## API

All routers are mounted in `app/main.py` under `/api/v1`.

---

### Client-scoped business creation (`/api/v1/clients/{client_id}/businesses`)

Roles: `ADVISOR` (create), `ADVISOR` + `SECRETARY` (list)

#### Create business
- `POST /api/v1/clients/{client_id}/businesses`
- Role: `ADVISOR` only
- Body:

```json
{
  "business_type": "osek_murshe",
  "opened_at": "2026-01-01",
  "business_name": "Cohen Consulting",
  "notes": "Optional"
}
```

- Behavior: validates client exists; if `business_name` is provided, enforces uniqueness per client (`BUSINESS.NAME_CONFLICT`)

#### List businesses for client
- `GET /api/v1/clients/{client_id}/businesses`
- Roles: `ADVISOR`, `SECRETARY`
- Returns all active businesses for the client

---

### Standalone business routes (`/api/v1/businesses`)

Roles: `ADVISOR`, `SECRETARY` unless noted

#### List businesses
- `GET /api/v1/businesses`
- Query params:
  - `status` (optional)
  - `business_type` (optional)
  - `has_signals` (optional boolean — advisory filter; bounded by `_HAS_SIGNALS_FETCH_LIMIT = 1000`)
  - `search` (optional — matches `business_name`, `client.full_name`, `client.id_number`)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)
- Response: `BusinessListResponse` — items are `BusinessWithClientResponse` (includes `client_full_name`, `client_id_number`)

#### Get business
- `GET /api/v1/businesses/{business_id}`
- Response: `BusinessResponse` with `available_actions`

#### Update business
- `PATCH /api/v1/businesses/{business_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Partial update. Transitioning to `frozen` or `closed` requires `ADVISOR` role (`BUSINESS.FORBIDDEN` otherwise)
- Setting `status=closed` auto-sets `closed_at=today` if not supplied

#### Delete business (soft delete)
- `DELETE /api/v1/businesses/{business_id}`
- Role: `ADVISOR` only
- Returns `204 No Content`

#### Restore business
- `POST /api/v1/businesses/{business_id}/restore`
- Role: `ADVISOR` only
- Restores a soft-deleted business; sets `status=active`, records `restored_at`, `restored_by`

#### Bulk status action
- `POST /api/v1/businesses/bulk-action`
- Role: `ADVISOR` only
- Body:

```json
{
  "business_ids": [1, 2, 3],
  "action": "freeze"
}
```

- `action` values: `freeze`, `close`, `activate`
- Partial-success by design — per-item failures are returned without aborting successful items
- Response: `BulkBusinessActionResponse` with `succeeded` and `failed` lists

---

### Tax profile (`/api/v1/businesses/{business_id}/tax-profile`)

Roles: `ADVISOR`, `SECRETARY`

#### Get tax profile
- `GET /api/v1/businesses/{business_id}/tax-profile`
- Returns empty `BusinessTaxProfileResponse` (with only `business_id`) if no profile exists yet

#### Update tax profile
- `PATCH /api/v1/businesses/{business_id}/tax-profile`
- Upserts the profile; creates on first call
- Updatable fields: `vat_type`, `vat_start_date`, `vat_exempt_ceiling`, `accountant_name`, `advance_rate` (0–100), `advance_rate_updated_at`, `fiscal_year_start_month` (1–12)

---

### Status card (`/api/v1/businesses/{business_id}/status-card`)

Roles: `ADVISOR`, `SECRETARY`

#### Get business status card
- `GET /api/v1/businesses/{business_id}/status-card`
- Query params:
  - `year` (optional, default = current year)
- Returns an aggregated operational snapshot:

| Section | Fields |
|---|---|
| `vat` | `net_vat_total`, `periods_filed`, `periods_total`, `latest_period` |
| `annual_report` | `status`, `form_type`, `filing_deadline`, `refund_due`, `tax_due` |
| `charges` | `total_outstanding`, `unpaid_count` |
| `advance_payments` | `total_paid`, `count` |
| `binders` | `active_count`, `in_office_count` |
| `documents` | `total_count`, `present_count` |

---

### Business binders (`/api/v1/businesses/{business_id}/binders`)

Roles: `ADVISOR`, `SECRETARY`

- `GET /api/v1/businesses/{business_id}/binders`
- Resolves `business.client_id` and returns that client's binders (paginated), enriched with `work_state` and `signals`
- See [Binders module](../binders/README.md) for full field reference

---

## Behavior Notes

- A client can hold multiple businesses — there is no uniqueness constraint on `(client_id, business_type)`.
- `business_name` uniqueness is enforced per client among non-deleted businesses.
- Businesses in `closed` or `frozen` status block new work creation in downstream domains (VAT, annual reports, binders, charges).
- The `has_signals` filter fetches up to `_HAS_SIGNALS_FETCH_LIMIT = 1000` businesses in memory; exceeding the limit raises `BUSINESS.SIGNAL_FILTER_LIMIT`.
- Repository reads (`get_by_id`, list/count) exclude soft-deleted records by default; `get_by_id_including_deleted` and `list_by_client_including_deleted` bypass this.
- `available_actions` on business responses are role-aware: `freeze` is only included for ADVISOR.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`:
- `detail`
- `error`
- `error_meta`

Domain errors:
- `BUSINESS.NOT_FOUND`
- `BUSINESS.CONFLICT` — integrity error on create
- `BUSINESS.NAME_CONFLICT` — duplicate `business_name` for the same client
- `BUSINESS.FORBIDDEN` — non-advisor attempted a status change to frozen/closed, or restore
- `BUSINESS.NOT_DELETED` — restore called on a non-deleted business
- `BUSINESS.INVALID_VAT_TYPE` — invalid value passed to tax profile update
- `BUSINESS.SIGNAL_FILTER_LIMIT` — `has_signals` filter exceeds in-memory ceiling
- `BUSINESS.CLOSED` / `BUSINESS.FROZEN` — raised by downstream domain guards when creating new work
- `CLIENT.NOT_FOUND` — client does not exist on business create

## Cross-Domain Integration

- `clients` — every business is owned by a client; `client_id` is required on create
- `binders` — business status card and binders endpoint resolve binders via `client_id`
- `vat_reports` — VAT work items are business-scoped; `vat_type` from `BusinessTaxProfile` drives period validation and deadline generation
- `annual_reports` — annual reports are business-scoped
- `advance_payments` — payments are business-scoped; `advance_rate` from tax profile drives suggestion calculation
- `tax_deadline` — deadline generator reads `vat_type` from `BusinessTaxProfile`
- `charges` — charges are business-scoped
- `permanent_documents` — documents are business-scoped
- `authority_contacts` — contacts are business-scoped (`/businesses/{id}/authority-contacts`)
- `correspondence` — entries are business-scoped (`/businesses/{id}/correspondence`)
- `signature_requests` — requests are business-scoped (`/businesses/{id}/signature-requests`)
- `timeline` — unified timeline is business-scoped (`/businesses/{id}/timeline`)
- `reminders` — reminders are business-scoped
- `notifications` — notifications are business-scoped
- `actions` — `get_business_actions` generates `available_actions` per status/role

## Tests

Business test suites:
- `tests/businesses/api/test_businesses.py`
- `tests/businesses/api/test_business_binders.py`
- `tests/businesses/service/test_business_service.py`
- `tests/businesses/repository/test_business_repository.py`

Run only this domain:

```bash
pytest tests/businesses -q
```
