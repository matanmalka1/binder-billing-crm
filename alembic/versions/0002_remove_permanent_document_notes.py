"""remove permanent document notes

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-27 00:00:00

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0002
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0001

Notes:
- Removes notes from permanent documents.
- Downgrade restores the nullable notes column without recovering deleted data.
- No PostgreSQL/SQLite differences.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("permanent_documents", "notes")


def downgrade() -> None:
    op.add_column("permanent_documents", sa.Column("notes", sa.String(), nullable=True))
