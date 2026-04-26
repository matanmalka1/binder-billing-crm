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
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_reminder_active",
        "reminders",
        ["client_record_id", "reminder_type", "target_date"],
        unique=True,
        postgresql_where=sa.text("status != 'canceled' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_reminder_active",
        table_name="reminders",
        postgresql_where=sa.text("status != 'canceled' AND deleted_at IS NULL"),
    )
