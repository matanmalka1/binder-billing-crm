# Binder Billing CRM

Production-ready FastAPI + SQLAlchemy backend for client records, physical binder lifecycle, and internal billing.

Sprint 5 is frozen (see `SPRINT_5_FREEZE_DECLARATION.md`). The system state is considered stable and non-contradictory with the frozen sprint documents.

## Roles & Permissions (High Level)
- `SECRETARY`: operational workflows (client/binder reads, operational binder lists, dashboard summary, permanent document upload & signals).
- `ADVISOR`: super-role (may perform all `SECRETARY` actions) + privileged actions (e.g., client status transitions and charge lifecycle operations).

## Implemented Modules by Sprint
- Sprint 1: core entities & binders (clients, binders, auth basics).
- Sprint 2: operational views & SLA (open/overdue/due-today lists, binder history, dashboard overview/summary; SLA derived at read time).
- Sprint 3: billing (charges & invoices; controlled charge lifecycle; external invoice references).
- Sprint 4: notifications, documents, background job (notification persistence & background processing; permanent document presence tracking & operational signals).
- Sprint 5: production hardening & cleanup (env validation, JWT expiration enforcement, structured logging + request IDs, centralized error handling, health endpoint, job resilience).

## Technical Constraints
- ORM-first architecture (SQLAlchemy ORM queries only)
- Layering: API -> Service -> Repository
- No raw SQL
- Sprints 3–4 introduced Alembic migrations for new tables only (see the sprint specs for the frozen policy and constraints).

## Documentation (Reading Order)
Read in this order:
1. `README.md` (this file)
2. `DEV_SETUP.md` (how to run locally + tests)
3. `API_CONTRACT.md` (route index + role-level access)
4. Sprint authoritative docs (frozen):
   - `SPRINT_3_FORMAL_SPECIFICATION.md`
   - `sprint_4_formal_specification.md` (see also `sprint_4_freeze_rules.md`)
   - `SPRINT_5_FORMAL_SPECIFICATION.md` (freeze declared in `SPRINT_5_FREEZE_DECLARATION.md`)
   - `SPRINT_2_IMPLEMENTATION.md` (historical Sprint 2 freeze summary)

## Quickstart
Follow `DEV_SETUP.md` for the full local setup. Common entrypoints:
- API: `python -m app.main`
- OpenAPI: `http://localhost:8000/docs`
- Health: `GET http://localhost:8000/health`
- Info: `GET http://localhost:8000/info`

## Tests
```bash
JWT_SECRET=test-secret pytest -q
```
