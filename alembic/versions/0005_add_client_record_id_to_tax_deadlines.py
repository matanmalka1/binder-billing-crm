"""add_client_record_id_to_tax_deadlines

Revision ID: 0005_add_client_record_id_to_tax_deadlines
Revises: 0004_add_client_record_id_to_vat_work_items
Create Date: 2026-04-19

Additive only: adds client_record_id FK to tax_deadlines. client_id retained.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_add_client_record_id_to_tax_deadlines"
down_revision: Union[str, None] = "0004_add_client_record_id_to_vat_work_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tax_deadlines",
        sa.Column("client_record_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tax_deadlines_client_record_id",
        "tax_deadlines",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index(
        "ix_tax_deadlines_client_record_id",
        "tax_deadlines",
        ["client_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tax_deadlines_client_record_id", table_name="tax_deadlines")
    op.drop_constraint("fk_tax_deadlines_client_record_id", "tax_deadlines", type_="foreignkey")
    op.drop_column("tax_deadlines", "client_record_id")
