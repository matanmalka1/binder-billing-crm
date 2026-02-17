# Binder Billing & Tax CRM

Production-ready FastAPI + SQLAlchemy backend for client records, binder lifecycle management, billing, notifications, tax workflows, and operational dashboards.

Backend scope: **implemented through Sprint 9** (Sprint 8 Tax CRM features + Sprint 9 reminder/architecture fixes).  
Any backend behavior or schema change now requires a new Sprint 10+ specification.

## Roles & Permissions (High Level)
- `SECRETARY`: operational workflows and read-oriented operational views.
- `ADVISOR`: super-role (may perform all `SECRETARY` actions) plus privileged financial and administrative actions.

## Documentation (Authoritative Reading Order)
1. `README.md` (this file)
2. `DEV_SETUP.md` (local setup and test execution)
3. `PROJECT_RULES.md` (highest-level engineering and architecture rules)
4. `API_CONTRACT.md` (authoritative API surface and route-level contract)
5. `SPRINT_8_README.md` (Tax CRM features summary)
6. `SPRINT_9_ARCHITECTURE.md` + `SPRINT_9_MIGRATION.md` + `SPRINT_9_SUMMARY.md` (reminder architecture fixes and migration guidance)
7. `SPRINT_6_FORMAL_SPECIFICATION.md` + `SPRINT_6_FREEZE_DECLARATION.md` (previous freeze baseline)
8. Earlier frozen authorities:
   - `SPRINT_3_FORMAL_SPECIFICATION.md`
   - `sprint_4_formal_specification.md`
   - `sprint_4_freeze_rules.md`
   - `SPRINT_5_FORMAL_SPECIFICATION.md`
   - `SPRINT_5_FREEZE_DECLARATION.md`

## Quickstart
Follow `DEV_SETUP.md` for full setup. Common entrypoints:
- API (local dev): `APP_ENV=development ENV_FILE=.env.development python -m app.main`
- OpenAPI: `http://localhost:8000/docs`
- Health: `GET http://localhost:8000/health`
- Info: `GET http://localhost:8000/info`

Note: an exported `DATABASE_URL` in your shell overrides values from `.env.*` (dotenv loads with `override=False`). If you expect SQLite locally but see Postgres being used, run `unset DATABASE_URL` (or override it inline for the command).

## Tests
```bash
JWT_SECRET=test-secret pytest -q
```

## Filter Options
All filter dropdown options in the frontend are defined in `src/constants/filterOptions.constants.ts`.

When adding or removing filter values:
1. Update the label mapper in `src/utils/enums.ts`.
2. Update the matching constant in `src/constants/filterOptions.constants.ts`.
3. Components will automatically consume the new values via the shared constants; avoid hardcoding options inside components.
