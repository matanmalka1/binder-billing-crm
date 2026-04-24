# Tax Deadline Module

> Last audited: 2026-03-22.

Manages client-record tax deadlines lifecycle (create/list/update/complete/reopen/delete), urgency views for dashboard, timeline projection, and yearly deadline generation.

## Scope

This module provides:
- Tax-deadline CRUD lifecycle over `tax_deadlines`
- Deadline completion tracking
- Reopen flow from `completed` back to `pending`
- Dashboard urgent/upcoming summary
- Client timeline endpoint
- Idempotent yearly deadline generation by client tax profile
- Automatic reminder creation on deadline creation (`days_before=7`)
- Role-based API access

## Domain Model

`TaxDeadline` (`app/tax_deadline/models/tax_deadline.py`) fields:
- `id` (PK)
- `client_record_id` (FK -> `client_records.id`, required)
- `deadline_type` (enum, required)
- `period` (`YYYY-MM`, optional)
- `due_date` (required)
- `status` (`pending`/`completed`/`canceled`, default `pending`)
- `completed_at` (optional)
- `completed_by` (optional FK -> `users.id`)
- `advance_payment_id` (optional FK -> `advance_payments.id`)
- `payment_amount` (optional)
- `description` (optional)
- `created_at`
- `deleted_at` / `deleted_by` (soft delete)

Deadline type enum values:
- `vat`
- `advance_payment`
- `national_insurance`
- `annual_report`
- `other`

Urgency levels (derived, not persisted):
- `green`
- `yellow`
- `red`
- `overdue`

## API

Routers are mounted with prefix `/api/v1`, and tax-deadline routers use `/tax-deadlines`.

### Access control

Default tax-deadline router access: `ADVISOR`, `SECRETARY`.

Advisor-only endpoints:
- `POST /api/v1/tax-deadlines`
- `POST /api/v1/tax-deadlines/{deadline_id}/complete`
- `POST /api/v1/tax-deadlines/{deadline_id}/reopen`
- `PUT /api/v1/tax-deadlines/{deadline_id}`
- `DELETE /api/v1/tax-deadlines/{deadline_id}`
- `POST /api/v1/tax-deadlines/generate`

Advisor + Secretary endpoints:
- `GET /api/v1/tax-deadlines`
- `GET /api/v1/tax-deadlines/{deadline_id}`
- `GET /api/v1/tax-deadlines/timeline`
- `GET /api/v1/tax-deadlines/dashboard/urgent`

### Create deadline

- `POST /api/v1/tax-deadlines`

Body:

```json
{
  "client_record_id": 123,
  "deadline_type": "vat",
  "due_date": "2026-04-15",
  "period": "2026-03",
  "payment_amount": 1500.5,
  "description": "VAT filing"
}
```

### List deadlines

- `GET /api/v1/tax-deadlines`
- Query params:
  - `client_record_id` (optional)
  - `business_name` (optional client-name substring filter)
  - `client_name` (legacy alias for `business_name`)
  - `deadline_type` (optional)
  - `status` (optional)
  - `due_from` (optional, `YYYY-MM-DD`)
  - `due_to` (optional, `YYYY-MM-DD`)
  - `period` (optional, `YYYY-MM`)
  - `page` (default `1`, min `1`)
  - `page_size` (default `20`, min `1`, max `100`)

Behavior:
- `client_record_id` present: returns all matching deadlines for that client record.
- `business_name` / `client_name` present: resolves client IDs by name then returns matching deadlines.
- no filters: returns paginated pending deadlines only, from today forward.

### Get deadline

- `GET /api/v1/tax-deadlines/{deadline_id}`

### Complete deadline

- `POST /api/v1/tax-deadlines/{deadline_id}/complete`
- Idempotent if already completed.

### Reopen deadline

- `POST /api/v1/tax-deadlines/{deadline_id}/reopen`
- Reverts a completed deadline to `pending`.

### Update deadline

- `PUT /api/v1/tax-deadlines/{deadline_id}`
- At least one editable field is required.
- Editable in service/repository:
  - `deadline_type`
  - `due_date`
  - `period`
  - `payment_amount`
  - `description`

### Delete deadline

- `DELETE /api/v1/tax-deadlines/{deadline_id}`
- Soft delete.
- Returns `204 No Content`.

### Timeline by client

- `GET /api/v1/tax-deadlines/timeline`
- Query params:
  - `client_record_id` (required)
- Returns due-date sorted entries with:
  - `days_remaining`
  - `urgency_level`
  - `milestone_label`

### Dashboard urgent summary

- `GET /api/v1/tax-deadlines/dashboard/urgent`
- Returns:
  - `urgent`: overdue + critical + warning deadlines
  - `upcoming`: pending deadlines in `[today, today+7]`

### Generate yearly deadlines

- `POST /api/v1/tax-deadlines/generate`

Body:

```json
{
  "client_record_id": 123,
  "year": 2026
}
```

Response:

```json
{
  "created_count": 0
}
```

## Generation Rules

`DeadlineGeneratorService` generates:
- VAT deadlines by `vat_type`:
  - `monthly` -> 12 deadlines
  - `bimonthly` -> 6 deadlines
  - `exempt`/missing profile -> none
- Advance-payment deadlines monthly (12)
- Annual report deadline once, derived by filing profile:
  - individual/manual: `May 29` of `year + 1`
  - individual/online: `June 30` of `year + 1`
  - corporation/control-holder: `July 31` of `year + 1`
- National-insurance deadlines are not auto-generated.

Generation is idempotent via repository `exists(client_record_id, deadline_type, due_date)` checks.

## Urgency Rules

Derived in query service for pending deadlines:
- `<0 days`: `overdue`
- `<=2 days`: `red`
- `<=7 days`: `yellow`
- `>7 days`: `green`

## Error Codes

Domain errors include:
- `TAX_DEADLINE.NOT_FOUND`
- `TAX_DEADLINE.NO_FIELDS_PROVIDED`

Error envelope follows the app-wide exception format.

## Integration Points

- `clients`:
  - client existence + create guards
  - client-name lookup for list enrichment
- `reminders`:
  - auto-reminder on create
- `business_tax_profile`:
  - VAT frequency for generator (looked up via client's associated business)
- `actions`:
  - `available_actions` via `app/actions/report_deadline_actions.py`

## Tests

Domain tests are under:
- `tests/tax_deadline/api/`
- `tests/tax_deadline/service/`
- `tests/tax_deadline/repository/`

Run:

```bash
JWT_SECRET=test-secret pytest -q tests/tax_deadline
```
