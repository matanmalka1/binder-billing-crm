"""Shared helpers for seeding fake demo data."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure local scripts can run even when JWT_SECRET is not exported in shell.
os.environ.setdefault("JWT_SECRET", "dev-seed-secret")
os.environ.setdefault("APP_ENV", "development")

# Make `app` imports work when running scripts directly
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

__all__ = ["ROOT_DIR"]
