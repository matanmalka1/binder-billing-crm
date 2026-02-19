#!/usr/bin/env python3
"""Populate the local database with fake but coherent demo data."""

from __future__ import annotations

from seed_fake_data_lib.config import parse_args
from seed_fake_data_lib.seeder import Seeder


def main() -> None:
    cfg = parse_args()
    Seeder(cfg).run()


if __name__ == "__main__":
    main()
