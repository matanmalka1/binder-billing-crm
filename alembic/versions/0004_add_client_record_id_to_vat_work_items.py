"""add_client_record_id_to_vat_work_items

Revision ID: 0004_add_client_record_id_to_vat_work_items
Revises: 0003_add_client_record_id_to_annual_reports
Create Date: 2026-04-19

Additive only: adds client_record_id FK to vat_work_items. client_id retained.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_add_client_record_id_to_vat_work_items"
down_revision: Union[str, None] = "0003_add_client_record_id_to_annual_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vat_work_items",
        sa.Column("client_record_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_vat_work_items_client_record_id",
        "vat_work_items",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index(
        "ix_vat_work_items_client_record_id",
        "vat_work_items",
        ["client_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_vat_work_items_client_record_id", table_name="vat_work_items")
    op.drop_constraint("fk_vat_work_items_client_record_id", "vat_work_items", type_="foreignkey")
    op.drop_column("vat_work_items", "client_record_id")
