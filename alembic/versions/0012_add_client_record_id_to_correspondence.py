"""add_client_record_id_to_correspondence

Revision ID: 0012_add_client_record_id_to_correspondence
Revises: 0011_add_client_record_id_to_notifications
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_add_client_record_id_to_correspondence"
down_revision: Union[str, None] = "0011_add_client_record_id_to_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("correspondence_entries", sa.Column("client_record_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_correspondence_entries_client_record_id",
        "correspondence_entries",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index("ix_correspondence_entries_client_record_id", "correspondence_entries", ["client_record_id"])


def downgrade() -> None:
    op.drop_index("ix_correspondence_entries_client_record_id", table_name="correspondence_entries")
    op.drop_constraint("fk_correspondence_entries_client_record_id", "correspondence_entries", type_="foreignkey")
    op.drop_column("correspondence_entries", "client_record_id")
