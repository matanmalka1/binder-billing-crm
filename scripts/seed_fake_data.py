#!/usr/bin/env python3
"""Populate the local database with fake but coherent demo data."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.seed_fake_data_lib.runtime import ensure_runtime


def main() -> None:
    ensure_runtime()
    from scripts.seed_fake_data_lib.config import parse_args
    from scripts.seed_fake_data_lib.seeder import Seeder

    cfg = parse_args()
    Seeder(cfg).run()


if __name__ == "__main__":
    main()
