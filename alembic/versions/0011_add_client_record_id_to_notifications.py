"""add_client_record_id_to_notifications

Revision ID: 0011_add_client_record_id_to_notifications
Revises: 0010_add_client_record_id_to_charges
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_add_client_record_id_to_notifications"
down_revision: Union[str, None] = "0010_add_client_record_id_to_charges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("client_record_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_notifications_client_record_id", "notifications", "client_records", ["client_record_id"], ["id"]
    )
    op.create_index("ix_notifications_client_record_id", "notifications", ["client_record_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_client_record_id", table_name="notifications")
    op.drop_constraint("fk_notifications_client_record_id", "notifications", type_="foreignkey")
    op.drop_column("notifications", "client_record_id")
