#!/usr/bin/env python3
"""Populate the local database with fake but coherent demo data.

Local quick start:
1) Run migrations:
   APP_ENV=development ENV_FILE=.env.development alembic upgrade head
2) Reset local DB and rerun from scratch when needed:
   - If you deleted tables manually, also reset the Alembic state in the same database.
   - Recommended full reset in development on PostgreSQL:
     DB_URL=$(grep '^DATABASE_URL=' .env.development | cut -d= -f2- | sed 's/^postgresql+psycopg2:/postgresql:/')
     psql "$DB_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   - Then run:
     APP_ENV=development ENV_FILE=.env.development alembic upgrade head
   - After the schema is back, rerun the relevant seed command below.
3) Run seed:
   APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --reset
   APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --users-only --reset
   APP_ENV=development ENV_FILE=.env.development python scripts/seed_fake_data.py --onboarding-only --reset
4) Run backend:
   APP_ENV=development ENV_FILE=.env.development python -m app.main
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_tax_rules_path = str(ROOT_DIR / "tax_rules_config" / "app")
if _tax_rules_path not in sys.path:
    sys.path.insert(0, _tax_rules_path)

os.environ.setdefault("JWT_SECRET", "dev-seed-secret")
os.environ.setdefault("APP_ENV", "development")


def main() -> None:
    from app.seed.config import parse_args
    from app.seed.orchestrator import SeedOrchestrator

    cfg = parse_args()
    SeedOrchestrator(cfg).run()


if __name__ == "__main__":
    main()
