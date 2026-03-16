from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_runtime() -> None:
    """
    Prepare runtime environment for local seed scripts.

    - Ensures safe defaults for local-only env vars.
    - Ensures project root is on sys.path so `app` imports work when executed
      as `python scripts/seed_fake_data.py`.
    """
    os.environ.setdefault("JWT_SECRET", "dev-seed-secret")
    os.environ.setdefault("APP_ENV", "development")

    root_dir = Path(__file__).resolve().parents[2]
    root_dir_str = str(root_dir)
    if root_dir_str not in sys.path:
        sys.path.insert(0, root_dir_str)
