"""add processing to reminderstatus enum

Revision ID: 8a3c1f2b9d4e
Revises: ff773718d72e
Create Date: 2026-03-23

Background job now claims reminders as PROCESSING before sending to prevent
double-sends on crash/restart between send and mark_sent.
"""

from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8a3c1f2b9d4e'
down_revision: Union[str, Sequence[str], None] = 'ff773718d72e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL: add new enum value (cannot be done inside a transaction).
    # SQLite: uses string columns, no DDL needed.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE reminderstatus ADD VALUE IF NOT EXISTS 'processing'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    # Rows with status='processing' would need manual cleanup before downgrading.
    pass
