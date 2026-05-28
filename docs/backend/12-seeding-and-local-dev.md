## Scope
This file owns only:
- Backend-local seeding and local development implementation details.
- Concrete seed data, local storage, and bootstrap notes subordinate to canonical YM_Docs workflow rules.

This file must not contain:
- Project-wide workflow rules that override YM_Docs.
- Product/domain behavior.
- Frontend setup rules.

Source of truth: reference

Canonical project-wide rules:
- `../../../docs/docs/workflow/commands.md`
- `../../../docs/docs/workflow/local-env.md`
- `../../../docs/docs/workflow/verification.md`

# Seeding and Local Dev

## Running the App

```bash
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python -m app.main
```

Docs: `http://localhost:8000/docs`

## Environment Variables

Set in `.env.development` (not committed):

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | Yes | `postgresql+psycopg2://...` |
| `JWT_SECRET` | Yes | Any non-empty string in dev |
| `CORS_ALLOWED_ORIGINS` | No | Defaults to localhost and 127.0.0.1 on ports 3000 and 5173 |
| `LOG_SQL` | No | Auto-set to `true` in development |
| `LOG_LEVEL` | No | Default `INFO` |

See `app/config.py` `Settings` class for the full list.

## Seed Data

`app/seed/` contains a seeding orchestrator with builders for the main demo-data domains.

Run seed (requires the DB schema to be up to date via Alembic):

```bash
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python scripts/seed_fake_data.py --reset
```

Seed behavior is controlled by `SeedConfig` from `app/seed/config.py`. Common options:
- `--reset` — truncates all non-user tables before seeding
- `--preserve-users` — keep existing users, reset everything else
- `--users-only` — create users only
- `--onboarding-only` — create clients and onboarding phase only
- `--seed <int>` — random seed for reproducibility

The seed orchestrator:
1. Imports all model modules so ORM mappers are ready
2. Validates that the DB schema is up to date (checks for missing tables/columns)
3. Optionally resets via `TRUNCATE ... RESTART IDENTITY CASCADE`
4. Creates users, clients, businesses
5. Runs `ClientOnboardingOrchestrator` which creates: initial binder, TaxCalendar entries, VAT items, advance payments, annual report shell
6. Creates historical demo data: binders, charges, invoices, reports, documents, signatures, notifications

### Schema Validation

`_ensure_schema_ready()` in `app/seed/orchestrator.py` compares `Base.metadata` against `inspector.get_table_names()` and `inspector.get_columns()`. If any tables or columns are missing it raises `RuntimeError` with a helpful message. Run `alembic upgrade head` first.

## Migrations

Canonical workflow rules: see `../../../docs/docs/workflow/commands.md` and `../../../docs/docs/workflow/local-env.md`. The commands below are backend-local detail.

```bash
# Generate migration after model change
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python -m alembic revision --autogenerate -m "<description>"

# Apply
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python -m alembic upgrade head
```

Migrations live in `alembic/versions/NNNN_<description>.py`. After running, update `alembic/README` with run notes.

## Storage in Dev

`LocalStorageProvider` writes files under `./storage/`. In dev, the `./storage/` directory is served at `/local-storage/*` via `StaticFiles`. File URLs from the API point to this path.

`get_storage_provider()` in `app/infrastructure/storage.py` returns `LocalStorageProvider` for `development` and `test`, and `S3StorageProvider` for `staging` and `production`.

## Tax Calendar Bootstrap

`run_development_tax_calendar_bootstrap()` runs at startup in development. It seeds default `DeadlineRule` rows from `app/tax_calendar/services/bootstrap.py` if they don't exist. This only runs in development — production seeds via the seed command or explicitly.

## Background Jobs in Dev

`daily_expiry_job()` runs as an `asyncio.create_task` from `lifespan`. It sleeps for `BACKGROUND_JOB_INTERVAL_SECONDS` (default 86,400 seconds) between runs and calls `expire_overdue_requests()` for overdue signature requests. In tests, this function is patched out in `tests/conftest.py` to prevent side effects.

## Notifications

`NOTIFICATIONS_ENABLED=false` by default (including production). When disabled, the email channel logs and returns success without sending; when enabled and configured it sends through Brevo. `WhatsAppChannel` sends through 360dialog when configured, otherwise it returns "not configured" so delivery can fall back to email.

## Running Tests

```bash
# Domain-scoped (fast — preferred)
JWT_SECRET=test-secret ./.venv/bin/python -m pytest -q tests/binders/

# Full suite
JWT_SECRET=test-secret ./.venv/bin/python -m pytest -q
```

Tests use SQLite in-memory. No Postgres required for tests.
