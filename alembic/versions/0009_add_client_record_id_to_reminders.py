"""add_client_record_id_to_reminders

Revision ID: 0009_add_client_record_id_to_reminders
Revises: 0008_backfill_client_record_ids_wave1
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_add_client_record_id_to_reminders"
down_revision: Union[str, None] = "0008_backfill_client_record_ids_wave1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reminders", sa.Column("client_record_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_reminders_client_record_id", "reminders", "client_records", ["client_record_id"], ["id"]
    )
    op.create_index("ix_reminders_client_record_id", "reminders", ["client_record_id"])


def downgrade() -> None:
    op.drop_index("ix_reminders_client_record_id", table_name="reminders")
    op.drop_constraint("fk_reminders_client_record_id", "reminders", type_="foreignkey")
    op.drop_column("reminders", "client_record_id")
