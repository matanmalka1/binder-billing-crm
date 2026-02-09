# Sprint 2 Implementation (Frozen)

> Scope note: This document is the frozen summary for **Sprint 2 only**. Later sprints (3–5) added additional modules (e.g., billing, migrations, notifications/documents, hardening). For current developer onboarding, start with `README.md` and `DEV_SETUP.md`, and treat the sprint specifications as authoritative.

## Included
- `GET /api/v1/binders/open`
- `GET /api/v1/binders/overdue`
- `GET /api/v1/binders/due-today`
- `GET /api/v1/clients/{client_id}/binders`
- `GET /api/v1/binders/{binder_id}/history`
- `GET /api/v1/dashboard/overview`

## Explicitly Excluded
- UI or frontend changes
- New roles or authorization redesign
- Background workers or scheduled jobs
- Schema evolution/migrations
- Raw SQL

## Authorization Mapping
- `ADVISOR` = admin-level access
- `SECRETARY` = operational-level access

Applied route guards:
- Operational binder endpoints: `ADVISOR`, `SECRETARY`
- Binder history endpoint: `ADVISOR`, `SECRETARY`
- Dashboard overview endpoint: `ADVISOR` only

## Read-Only Confirmation (Sprint 2)
- Sprint 2 endpoints are read APIs.
- SLA state is derived at query time and not persisted.
- Binder overdue data is computed, not mutatively updated by Sprint 2 endpoints.

## Architecture and Policy
- ORM-first repository access only
- No raw SQL statements in app/test code
- API -> Service -> Repository separation preserved
- No migration files/tooling kept in repository

## Validation Snapshot
- Automated tests: `6 passed`
- Python file limit check: all Python files <= 150 lines
- Scope check: Sprint 2 additions are query/reporting/auth-guarded read endpoints
