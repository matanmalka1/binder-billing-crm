# Binder Billing CRM

FastAPI + SQLAlchemy backend for client records and physical binder lifecycle.

## Documentation
- API surface (frozen through Sprint 2): `API_CONTRACT.md`
- Sprint 2 freeze summary (authoritative for Sprint 2): `SPRINT_2_IMPLEMENTATION.md`
- Sprint 3 (authoritative if populated): `SPRINT_3_FORMAL_SPECIFICATION.md` (frozen)

## Sprint 2 Scope
- Operational binder query APIs: open, overdue, due-today, by-client
- Binder history read API
- Dashboard overview API
- Role-based guards: `ADVISOR` (admin-level), `SECRETARY` (operational-level)
- SLA derivation at read time (`is_overdue`, `days_overdue`)

## Sprint 2 Exclusions
- No UI/frontend work
- No new roles or auth redesign
- No background jobs
- No migration tooling in repository
- No raw SQL

## Technical Constraints
- ORM-first architecture (SQLAlchemy ORM queries only)
- Layering: API -> Service -> Repository
- No database migrations in this repository (any Sprint 3 policy changes must be defined in `SPRINT_3_FORMAL_SPECIFICATION.md`)

## Run
```bash
cp .env.example .env
pip install -r requirements.txt
python -m app.main
```

- API base URL: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

## Tests
```bash
JWT_SECRET=test-secret .venv/bin/pytest -q
```
