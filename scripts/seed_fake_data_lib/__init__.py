"""Shared helpers for seeding fake demo data."""

from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

__all__ = ["ROOT_DIR"]
