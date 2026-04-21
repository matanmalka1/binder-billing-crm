"""add canceled to tax deadline status

Revision ID: 7a9c5f4d2e11
Revises: 6392237139d9
Create Date: 2026-04-21 16:55:00.000000

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 7a9c5f4d2e11
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 6392237139d9

Notes:
- Aligns the PostgreSQL `taxdeadlinestatus` enum with the runtime model, which already
  includes the `canceled` terminal state.
- SQLite has no enum DDL here, so the migration is a no-op outside PostgreSQL.
- Downgrade is intentionally a no-op because PostgreSQL enum values cannot be removed safely.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a9c5f4d2e11"
down_revision: Union[str, Sequence[str], None] = "6392237139d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("ALTER TYPE taxdeadlinestatus ADD VALUE IF NOT EXISTS 'canceled'"))


def downgrade() -> None:
    pass
