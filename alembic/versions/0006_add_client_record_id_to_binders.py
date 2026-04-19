"""add_client_record_id_to_binders

Revision ID: 0006_add_client_record_id_to_binders
Revises: 0005_add_client_record_id_to_tax_deadlines
Create Date: 2026-04-19

Additive only: adds client_record_id FK to binders. client_id retained.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_add_client_record_id_to_binders"
down_revision: Union[str, None] = "0005_add_client_record_id_to_tax_deadlines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "binders",
        sa.Column("client_record_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_binders_client_record_id",
        "binders",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index(
        "ix_binders_client_record_id",
        "binders",
        ["client_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_binders_client_record_id", table_name="binders")
    op.drop_constraint("fk_binders_client_record_id", "binders", type_="foreignkey")
    op.drop_column("binders", "client_record_id")
