# scripts/

Utility scripts for local development, data seeding, manual API examples, and
one-time operational migrations.

## Scripts

| File | Purpose |
|---|---|
| `seed_fake_data.py` | Populate local DB with fake but coherent demo data |
| `bootstrap_tax_calendar.py` | Seed default tax calendar rules and generated calendar entries |
| `bootstrap_user_production.py` | Create a login user directly in the database |
| `migrate_official_name.py` | One-time migration: `Client.full_name` -> `LegalEntity.official_name` |
| `json_examples.py` | Generate sample JSON payloads and API contract docs for manual API testing |

## General Notes

- Run scripts from the backend repository root.
- Run Alembic migrations before seeding. The schema must exist before any seed command.
- `seed_fake_data.py` and `bootstrap_tax_calendar.py` default missing `JWT_SECRET` to `dev-seed-secret` and missing `APP_ENV` to `development`.
- Prefer `APP_ENV=development ENV_FILE=.env.development ...` for local commands.
- Use production scripts only with the correct `ENV_FILE`, `DATABASE_URL`, and `JWT_SECRET` loaded.

## Seed Fake Data

Creates local demo data across the app domains. Defaults include:

| Flag | Default |
|---|---:|
| `--users` | `8` |
| `--clients` | `60` |
| `--min-binders-per-client` | `1` |
| `--max-binders-per-client` | `3` |
| `--min-charges-per-client` | `3` |
| `--max-charges-per-client` | `8` |
| `--annual-reports-per-client` | `3` |
| `--min-vat-work-items-per-client` | `6` |
| `--max-vat-work-items-per-client` | `12` |
| `--min-vat-invoices-per-work-item` | `3` |
| `--max-vat-invoices-per-work-item` | `12` |
| `--signature-requests-per-client` | `2` |
| `--min-authority-contacts-per-client` | `1` |
| `--max-authority-contacts-per-client` | `3` |
| `--seed` | `42` |
| `--reference-date` | today's date |

Notes:

- `--reset` clears and rebuilds seeded data.
- `--preserve-users` keeps existing users, which avoids invalidating active JWTs.
- `--users-only` creates only users and requires at least one user.
- `--onboarding-only` seeds baseline onboarding data without the full historical dataset.
- `--skip-validation` skips seed integrity validation.
- If tables were deleted manually, reset the Alembic state in the same database before seeding again.
- If the script reports missing tables/columns, run `alembic upgrade head` first.

Quick start:

```bash
APP_ENV=development ENV_FILE=.env.development alembic upgrade head
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset
APP_ENV=development ENV_FILE=.env.development python -m app.main
```

Common variants:

```bash
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --onboarding-only
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --users-only --reset
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --preserve-users
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --reference-date 2026-05-03
```

Full PostgreSQL schema reset for development:

```bash
DB_URL=$(grep '^DATABASE_URL=' .env.development | cut -d= -f2- | sed 's/^postgresql+psycopg2:/postgresql:/')
psql "$DB_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
APP_ENV=development ENV_FILE=.env.development alembic upgrade head
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --users-only --reset
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset
```

## Bootstrap Tax Calendar

Seeds tax calendar rows through the tax calendar service.

Notes:

- Optional `--start-year` and `--end-year` limit the generated year range.
- The script commits on success and rolls back on failure.
- The script prints the service result as JSON.
- If the result includes warnings, they are printed after the JSON output.

Commands:

```bash
APP_ENV=development ENV_FILE=.env.development python scripts/bootstrap_tax_calendar.py
APP_ENV=development ENV_FILE=.env.development python scripts/bootstrap_tax_calendar.py --start-year 2026 --end-year 2027
```

## Bootstrap User

Creates an initial backend user for login.

Arguments:

| Flag | Required | Notes |
|---|---|---|
| `--full-name` | yes | User full name |
| `--email` | yes | Login identifier; normalized with trim + lowercase |
| `--password` | yes | Plain password; validated before hashing |
| `--role` | no | Defaults to `advisor`; choices come from `UserRole` |
| `--phone` | no | Optional phone number |
| `--fail-if-exists` | no | Return exit code `1` when the email already exists; default is print and exit `0` |

Production example:

```bash
APP_ENV=production ENV_FILE=.env.production JWT_SECRET=... \
python scripts/bootstrap_user_production.py \
  --full-name "Admin" \
  --email admin@example.com \
  --password 'SecurePass1!' \
  --role advisor
```

## Migrate Official Name

One-time data migration from `Client.full_name` to `LegalEntity.official_name`.

Notes:

- Run on development first, verify the result, then run on production.
- Safe to re-run. Existing `LegalEntity.official_name` values are skipped.
- Updates only active clients where `clients.deleted_at IS NULL`.
- Matches rows by `id_number` and `id_number_type`.
- After running, the script prints any `legal_entities` still missing `official_name`.

Command:

```bash
APP_ENV=development ENV_FILE=.env.development python scripts/migrate_official_name.py
```

## JSON Examples

Generates sample request/response payloads from the FastAPI app for manual API testing.

Notes:

- Imports `app.main:app`, so it reflects the current OpenAPI schema.
- Uses manual success overrides for binary/export endpoints and selected public/report endpoints.
- Generated examples are documentation/testing helpers, not source-of-truth business rules.
