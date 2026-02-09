# Binder Billing CRM

FastAPI + SQLAlchemy backend for client records and physical binder lifecycle.

## Documentation
- API surface (implemented through Sprint 3): `API_CONTRACT.md`
- Sprint 2 freeze summary (historical, authoritative for Sprint 2): `SPRINT_2_IMPLEMENTATION.md`
- Sprint 3 billing spec (authoritative, frozen): `SPRINT_3_FORMAL_SPECIFICATION.md`
- Sprint 3 implementation notes (historical): `SPRINT_3_IMPLEMENTATION_SUMMARY.md`
- Sprint 4 documents (authoritative for Sprint 4; do not infer Sprint 4 from older docs):
  - `sprint_4_formal_specification.md`
  - `sprint_4_freeze_rules.md`
  - `SPRINT_4_EXECUTION_PROMPT_CLAUDE.md`
  - `SPRINT_4_TEST_PLAN.md`
  - `SPRINT_4_TASK_BREAKDOWN.md`

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
- Sprint 3 introduced Alembic for the billing tables only (see `SPRINT_3_FORMAL_SPECIFICATION.md` for the frozen policy).

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
