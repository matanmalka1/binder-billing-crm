"""add_client_record_id_to_charges

Revision ID: 0010_add_client_record_id_to_charges
Revises: 0009_add_client_record_id_to_reminders
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_add_client_record_id_to_charges"
down_revision: Union[str, None] = "0009_add_client_record_id_to_reminders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("charges", sa.Column("client_record_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_charges_client_record_id", "charges", "client_records", ["client_record_id"], ["id"]
    )
    op.create_index("ix_charges_client_record_id", "charges", ["client_record_id"])


def downgrade() -> None:
    op.drop_index("ix_charges_client_record_id", table_name="charges")
    op.drop_constraint("fk_charges_client_record_id", "charges", type_="foreignkey")
    op.drop_column("charges", "client_record_id")
