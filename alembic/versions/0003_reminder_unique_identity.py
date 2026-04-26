"""reminder_unique_identity

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-26 12:10:00.000000

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0003
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0002

Notes:
- Adds DB-level uniqueness for non-canceled active reminder identity.
- Existing duplicate active rows must be resolved before upgrade if present.
- No-op because the initial schema already creates this index.
"""
from typing import Sequence, Union

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
