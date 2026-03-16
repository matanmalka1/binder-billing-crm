# Tax Deadline Module

Manages client tax deadlines lifecycle (create/list/update/complete/delete), urgency views for dashboard, timeline projection, and automatic yearly deadline generation.

## Scope

This module provides:
- CRUD-like management for `tax_deadlines`
- Deadline completion tracking
- Dashboard urgent/upcoming deadlines summary
- Client deadline timeline endpoint
- Idempotent yearly deadline generation by client profile
- Automatic reminder creation when a deadline is created
- Role-based API access

## Domain Model

`TaxDeadline` fields:
- `id` (PK)
- `client_id` (FK -> `clients.id`, required)
- `deadline_type` (enum, required)
- `due_date` (required)
- `status` (enum, default `pending`)
- Financial fields:
  - `payment_amount` (optional)
  - `currency` (default `ILS`)
- Metadata:
  - `description` (optional)
  - `created_at`
  - `completed_at` (optional)

Deadline type enum values:
- `vat`
- `advance_payment`
- `national_insurance`
- `annual_report`
- `other`

Status enum values:
- `pending`
- `completed`

Urgency levels (derived, not persisted):
- `green`
- `yellow`
- `red`
- `overdue`

Implementation references:
- Model: `app/tax_deadline/models/tax_deadline.py`
- Schemas: `app/tax_deadline/schemas/tax_deadline.py`
- Repository: `app/tax_deadline/repositories/tax_deadline_repository.py`
- Services: `app/tax_deadline/services/tax_deadline_service.py`, `app/tax_deadline/services/deadline_generator.py`, `app/tax_deadline/services/timeline_service.py`
- APIs: `app/tax_deadline/api/tax_deadline.py`, `app/tax_deadline/api/deadline_generate.py`

## API

Router prefix is `/api/v1/tax-deadlines` (mounted in `app/main.py`).

### Create deadline
- `POST /api/v1/tax-deadlines`
- Roles: `ADVISOR`, `SECRETARY`
- Body:

```json
{
  "client_id": 123,
  "deadline_type": "vat",
  "due_date": "2026-04-19",
  "payment_amount": 1500.5,
  "description": "VAT filing"
}
```

### List deadlines
- `GET /api/v1/tax-deadlines`
- Roles: `ADVISOR`, `SECRETARY`
- Query params:
  - `client_id` (optional)
  - `client_name` (optional substring)
  - `deadline_type` (optional)
  - `status` (optional)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

### Get deadline
- `GET /api/v1/tax-deadlines/{deadline_id}`
- Roles: `ADVISOR`, `SECRETARY`

### Complete deadline
- `POST /api/v1/tax-deadlines/{deadline_id}/complete`
- Roles: `ADVISOR`, `SECRETARY`

### Update deadline
- `PUT /api/v1/tax-deadlines/{deadline_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Editable fields:
  - `deadline_type`
  - `due_date`
  - `payment_amount`
  - `description`

### Delete deadline
- `DELETE /api/v1/tax-deadlines/{deadline_id}`
- Roles: `ADVISOR`, `SECRETARY`
- Returns `204 No Content`

### Timeline by client
- `GET /api/v1/tax-deadlines/timeline?client_id={id}`
- Roles: `ADVISOR`, `SECRETARY`
- Returns due-date ordered entries with:
  - `days_remaining`
  - `milestone_label`

### Dashboard urgent summary
- `GET /api/v1/tax-deadlines/dashboard/urgent`
- Roles: `ADVISOR`, `SECRETARY`
- Returns:
  - `urgent` (overdue/red/yellow)
  - `upcoming` (next 7 days)

### Generate yearly deadlines
- `POST /api/v1/tax-deadlines/generate`
- Role: `ADVISOR` only
- Body:

```json
{
  "client_id": 123,
  "year": 2026
}
```

- Returns:

```json
{
  "created_count": 0
}
```

## Behavior Notes

- Creating a deadline validates client existence and auto-creates a reminder (`days_before=7`).
- `mark_completed` is idempotent for already-completed deadlines.
- Update requires at least one field (`TAX_DEADLINE.NO_FIELDS_PROVIDED` otherwise).
- Listing behavior:
  - With `client_id`/`client_name`: filtered client-scope listing.
  - Without client filters: returns pending deadlines, bounded by `_GLOBAL_DEADLINE_FETCH_LIMIT = 500` before pagination.
- Urgency computation (pending deadlines only):
  - `<0 days`: `overdue`
  - `<=2 days`: `red`
  - `<=7 days`: `yellow`
  - `>7 days`: `green`
- Generator behavior (`generate_all`):
  - VAT deadlines generated from client VAT profile (`monthly`/`bimonthly`; none for exempt/undefined).
  - Advance-payment deadlines generated monthly.
  - Annual-report deadline generated once per year.
  - Uses repository `exists(...)` check so generation is idempotent.

## Error Envelope

Errors follow the global app format from `app/core/exceptions.py`, including:
- `detail`
- `error`
- `error_meta`

Domain errors use stable codes such as:
- `TAX_DEADLINE.NOT_FOUND`
- `TAX_DEADLINE.NO_FIELDS_PROVIDED`

Other related domain errors may surface via integrations (for example client/reminder validations).

## Cross-Domain Integration

- `clients` integration:
  - Deadline CRUD is client-scoped; name-based filtering uses client search.
- `reminders` integration:
  - Deadline creation triggers tax-deadline reminder creation.
- `client_tax_profile` integration:
  - Deadline generator reads VAT filing frequency (`monthly`/`bimonthly`/`exempt`).
- `actions` integration:
  - Deadline responses include `available_actions` from `app/actions/report_deadline_actions.py`.

## Tests

Tax-deadline test suites:
- `tests/tax_deadline/api/test_tax_deadline.py`
- `tests/tax_deadline/api/test_tax_deadline_crud.py`
- `tests/tax_deadline/api/test_tax_deadline_dashboard.py`
- `tests/tax_deadline/service/test_tax_deadline.py`
- `tests/tax_deadline/service/test_tax_deadline_service_get_client_deadlines.py`
- `tests/tax_deadline/repository/test_tax_deadline_repository.py`

Run only this domain:

```bash
pytest tests/tax_deadline -q
```
