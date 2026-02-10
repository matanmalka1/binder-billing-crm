# Binder Billing CRM

Production-ready FastAPI + SQLAlchemy backend for client records, binder lifecycle management, billing, notifications, and operational workflows.

Backend status: **frozen through Sprint 6**.  
No backend behavior, schema, or contract changes are allowed without a new sprint (**Sprint 7+**).

## Roles & Permissions (High Level)
- `SECRETARY`: operational workflows and read-oriented operational views.
- `ADVISOR`: super-role (may perform all `SECRETARY` actions) plus privileged financial and administrative actions.

## Documentation (Authoritative Reading Order)
1. `README.md` (this file)
2. `DEV_SETUP.md` (local setup and test execution)
3. `PROJECT_RULES.md` (highest-level engineering and architecture rules)
4. `API_CONTRACT.md` (authoritative API surface and route-level contract)
5. `SPRINT_6_FORMAL_SPECIFICATION.md` (Sprint 6 scope and constraints)
6. `SPRINT_6_TASK_BREAKDOWN.md` (Sprint 6 execution contract)
7. `SPRINT_6_FREEZE_DECLARATION.md` (formal Sprint 6 freeze state)
8. Prior frozen sprint authorities:
   - `SPRINT_3_FORMAL_SPECIFICATION.md`
   - `sprint_4_formal_specification.md`
   - `sprint_4_freeze_rules.md`
   - `SPRINT_5_FORMAL_SPECIFICATION.md`
   - `SPRINT_5_FREEZE_DECLARATION.md`

## Quickstart
Follow `DEV_SETUP.md` for full setup. Common entrypoints:
- API: `python -m app.main`
- OpenAPI: `http://localhost:8000/docs`
- Health: `GET http://localhost:8000/health`
- Info: `GET http://localhost:8000/info`

## Tests
```bash
JWT_SECRET=test-secret pytest -q
```
