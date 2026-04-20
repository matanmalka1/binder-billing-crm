#!/usr/bin/env python3
"""
One-time data migration: Client.full_name → LegalEntity.official_name

Run on dev first, verify, then on production.
Safe to re-run — skips LegalEntity rows that already have official_name set.

Usage:
    APP_ENV=development ENV_FILE=.env.development python scripts/migrate_official_name.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import text

from app.database import SessionLocal


def run() -> None:
    db = SessionLocal()
    try:
        results = db.execute(text("""
            UPDATE legal_entities le
            SET official_name = c.full_name
            FROM clients c
            WHERE le.id_number = c.id_number
              AND le.id_number_type::text = c.id_number_type::text
              AND le.official_name IS NULL
              AND c.deleted_at IS NULL
        """))
        db.commit()
        print(f"Updated {results.rowcount} legal_entity rows")

        missing = db.execute(text(
            "SELECT id, id_number FROM legal_entities WHERE official_name IS NULL"
        )).fetchall()
        if missing:
            print(f"WARNING: {len(missing)} legal_entities still have no official_name:")
            for row in missing:
                print(f"  id={row.id}, id_number={row.id_number}")
        else:
            print("All legal_entities have official_name set.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
