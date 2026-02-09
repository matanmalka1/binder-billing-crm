# Binder Billing CRM

FastAPI + SQLAlchemy backend for client records and physical binder lifecycle.

## Documentation
- API surface (implemented through Sprint 3): `API_CONTRACT.md`
- Sprint 2 freeze summary (historical, authoritative for Sprint 2): `SPRINT_2_IMPLEMENTATION.md`
- Sprint 3 billing spec (authoritative, frozen): `SPRINT_3_FORMAL_SPECIFICATION.md`
- Sprint 4 spec and freeze rules (authoritative for Sprint 4):
  - `sprint_4_formal_specification.md`
  - `sprint_4_freeze_rules.md`
- Sprint 5 spec (authoritative, frozen): `SPRINT_5_FORMAL_SPECIFICATION.md`

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
- No raw SQL

## Technical Constraints
- ORM-first architecture (SQLAlchemy ORM queries only)
- Layering: API -> Service -> Repository
- No raw SQL
- Sprints 3–4 introduced Alembic migrations for new tables only (see the sprint specs for the frozen policy).

## Run
```bash
cp .env.example .env
pip install -r requirements.txt
python -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)"
python -m app.main
```

- API base URL: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

## Tests
```bash
JWT_SECRET=test-secret .venv/bin/pytest -q
```
