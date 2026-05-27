"""add skipped value to notificationstatus enum

Revision ID: 0005_notification_status_skipped
Revises: 0004_notification_schema_v2
Create Date: 2026-05-27

ALTER TYPE ... ADD VALUE cannot run inside a transaction on PostgreSQL < 12.
Uses Alembic's autocommit_block() to commit the surrounding transaction first,
then execute the ADD VALUE outside any transaction.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_notification_status_skipped"
down_revision: Union[str, Sequence[str], None] = "0004_notification_schema_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE notificationstatus ADD VALUE IF NOT EXISTS 'skipped'"))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    # To roll back: recreate the enum without 'skipped' and migrate rows manually.
    pass
