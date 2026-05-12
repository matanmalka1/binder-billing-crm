# scripts/

Utility scripts for local development, data seeding, and one-time migrations.

## Scripts

| File | Purpose |
|---|---|
| `seed_fake_data.py` | Populate local DB with 60 clients and full demo data across all 21 domains |
| `bootstrap_tax_calendar.py` | Seed default tax calendar rules and generated calendar entries |
| `bootstrap_user_production.py` | Create a login user directly in the database (dev or production) |
| `migrate_official_name.py` | One-time migration: `Client.full_name` → `LegalEntity.official_name` |
| `json_examples.py` | Sample JSON payloads for manual API testing |

## Seed Quick Start

```bash
# 1. Run migrations (schema must exist before seeding)
APP_ENV=development ENV_FILE=.env.development alembic upgrade head

# 2. Full reset + reseed. Default seed includes coherent history.
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset

# 3. Seed only baseline onboarding data, without history.
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --onboarding-only

# 4. Seed only users (useful after wiping and re-migrating)
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --users-only --reset

# 5. Reseed keeping existing users (avoids invalidating JWTs)
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --preserve-users

# Optional deterministic business date:
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset --reference-date 2026-05-03
```

## Bootstrap Tax Calendar

```bash
APP_ENV=development ENV_FILE=.env.development python scripts/bootstrap_tax_calendar.py
APP_ENV=development ENV_FILE=.env.development python scripts/bootstrap_tax_calendar.py --start-year 2026 --end-year 2027
```

For full schema reset on PostgreSQL:

```bash
DB_URL=$(grep '^DATABASE_URL=' .env.development | cut -d= -f2- | sed 's/^postgresql+psycopg2:/postgresql:/')
psql "$DB_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
APP_ENV=development ENV_FILE=.env.development alembic upgrade head
APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --users-only --reset

APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset
```

See [seed_fake_data_lib/README.md](seed_fake_data_lib/README.md) for full flag reference and file layout.

## Bootstrap a User

```bash
# Create an advisor on production:
APP_ENV=production ENV_FILE=.env.production JWT_SECRET=... \
python scripts/bootstrap_user_production.py \
  --full-name "Admin" \
  --email admin@example.com \
  --password 'SecurePass1!' \
  --role advisor
```
