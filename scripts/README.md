# scripts/

Utility scripts for local development, data seeding, manual API examples, and one-time operational migrations.

---

## Index

| File | Category | Purpose |
|---|---|---|
| `reset_dev_db.py` | Dev | Full dev DB reset: drop schema, squash migrations, seed |
| `seed_fake_data.py` | Dev | Populate local DB with fake but coherent demo data |
| `bootstrap_tax_calendar.py` | Dev / Prod | Seed default tax calendar rules and generated entries |
| `bootstrap_user_production.py` | Dev / Prod | Create a login user directly in the database |
| `migrate_official_name.py` | One-time | `Client.full_name` → `LegalEntity.official_name` data migration |
| `export_openapi.py` | Tooling | Export current FastAPI OpenAPI schema to `openapi.json` |
| `check_contract_sync.py` | Tooling | Verify `openapi.json` matches the current FastAPI app schema |
| `list_routes.py` | Tooling | Print registered FastAPI routes, optionally filtered |
| `json_examples.py` | Tooling | Generate sample JSON payloads for manual API testing |

---

## General Notes

- Run all scripts from the backend repository root.
- Run `alembic upgrade head` before any seed script — schema must exist first.
- `seed_fake_data.py` and `bootstrap_tax_calendar.py` default missing `JWT_SECRET` to `dev-seed-secret` and missing `APP_ENV` to `development`.
- Prefer `APP_ENV=development ENV_FILE=.env.development ...` for all local commands.
- Use production scripts only with the correct `ENV_FILE`, `DATABASE_URL`, and `JWT_SECRET` loaded.

---

## reset_dev_db.py

Full local reset: drops the public schema, deletes all migration files, autogenerates a single fresh migration, runs `alembic upgrade head`, verifies model/schema sync with `alembic check`, then seeds fake data.

> **⚠️ Production warning:** If production has existing migrations, squashing them here will break the next deploy. You must reset production manually before deploying after running this script.

**Flags:**

| Flag | Default | Notes |
|---|---|---|
| `--yes` / `-y` | false | Skip confirmation prompt |
| `--preserve-users` | false | Keep existing users in seed step |
| `--clients` | `60` | Number of fake clients to seed |

**Commands:**

```bash
APP_ENV=development ENV_FILE=.env.development python scripts/reset_dev_db.py
APP_ENV=development ENV_FILE=.env.development python scripts/reset_dev_db.py --yes
APP_ENV=development ENV_FILE=.env.development python scripts/reset_dev_db.py --yes --preserve-users
APP_ENV=development ENV_FILE=.env.development python scripts/reset_dev_db.py --yes --clients 20
```

---

## seed_fake_data.py

Creates local demo data across all app domains. Idempotent with `--reset`.

**Flags:**

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
| `--reference-date` | today |

**Mode flags:**

- `--reset` — clear and rebuild all seeded data
- `--preserve-users` — keep existing users (avoids invalidating active JWTs)
- `--users-only` — create only users; requires at least one user
- `--onboarding-only` — seed baseline onboarding data without full historical dataset
- `--skip-validation` — skip seed integrity validation

**Notes:**

- If tables were deleted manually, reset the Alembic state in the same database before seeding again.
- If the script reports missing tables/columns, run `alembic upgrade head` first.

**Quick start:**

```bash
APP_ENV=development ENV_FILE=.env.development alembic upgrade head
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset
APP_ENV=development ENV_FILE=.env.development python -m app.main
```

**Common variants:**

```bash
# Onboarding data only
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --onboarding-only

# Users only
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --users-only --reset

# Reset without re-creating users
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --preserve-users

# Seed relative to a specific date
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --reference-date 2026-05-03
```

---

## bootstrap_tax_calendar.py

Seeds tax calendar rows through the tax calendar service. Commits on success, rolls back on failure. Prints the service result as JSON; warnings are printed after.

**Flags:**

| Flag | Notes |
|---|---|
| `--start-year` | Limit generated year range (optional) |
| `--end-year` | Limit generated year range (optional) |

**Commands:**

```bash
APP_ENV=development ENV_FILE=.env.development python scripts/bootstrap_tax_calendar.py
APP_ENV=development ENV_FILE=.env.development python scripts/bootstrap_tax_calendar.py --start-year 2026 --end-year 2027
```

---

## bootstrap_user_production.py

Creates an initial backend user for login. Safe to run on dev or prod.

**Flags:**

| Flag | Required | Notes |
|---|---|---|
| `--full-name` | yes | User full name |
| `--email` | yes | Login identifier; normalized with trim + lowercase |
| `--password` | yes | Plain password; validated before hashing |
| `--role` | no | Defaults to `advisor`; choices from `UserRole` |
| `--phone` | no | Optional phone number |
| `--fail-if-exists` | no | Exit code `1` when email already exists; default exits `0` |

**Production example:**

```bash
APP_ENV=production ENV_FILE=.env.production JWT_SECRET=... \
python scripts/bootstrap_user_production.py \
  --full-name "Admin" \
  --email admin@example.com \
  --password 'SecurePass1!' \
  --role advisor
```

---

## migrate_official_name.py

One-time data migration: copies `Client.full_name` → `LegalEntity.official_name`.

**Notes:**

- Run on development first, verify the result, then run on production.
- Safe to re-run — existing `LegalEntity.official_name` values are skipped.
- Updates only active clients where `clients.deleted_at IS NULL`.
- Matches rows by `id_number` and `id_number_type`.
- After running, prints any `legal_entities` still missing `official_name`.

**Command:**

```bash
APP_ENV=development ENV_FILE=.env.development python scripts/migrate_official_name.py
```

---

## export_openapi.py

Writes the current FastAPI OpenAPI schema to `openapi.json`. Imports `app.main:app` so it always reflects the live schema.

**Commands:**

```bash
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python scripts/export_openapi.py

# Custom output path
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python scripts/export_openapi.py --output /tmp/openapi.json
```

---

## check_contract_sync.py

Fails (non-zero exit) when `openapi.json` does not match the current FastAPI app schema. Use in CI or pre-deploy checks.

**Commands:**

```bash
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python scripts/check_contract_sync.py

# Custom schema path
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python scripts/check_contract_sync.py --path /tmp/openapi.json
```

---

## list_routes.py

Prints all registered FastAPI routes. The optional argument filters by path, route name, or tag.

**Commands:**

```bash
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python scripts/list_routes.py
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python scripts/list_routes.py notifications
APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python scripts/list_routes.py audit
```

---

## json_examples.py

Generates sample request/response payloads from the FastAPI app for manual API testing.

**Notes:**

- Imports `app.main:app`, so it reflects the current OpenAPI schema.
- Uses manual success overrides for binary/export endpoints and selected public/report endpoints.
- Generated examples are documentation/testing helpers, not source-of-truth business rules.
