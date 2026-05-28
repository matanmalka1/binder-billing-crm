#!/usr/bin/env python3
"""Populate the local database with fake but coherent demo data.

For a full DB reset (drop schema + squash migrations + seed), use reset_dev_db.py instead.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
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
