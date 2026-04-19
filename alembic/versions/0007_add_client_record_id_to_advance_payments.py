"""add_client_record_id_to_advance_payments

Revision ID: 0007_add_client_record_id_to_advance_payments
Revises: 0006_add_client_record_id_to_binders
Create Date: 2026-04-19

Additive only: adds client_record_id FK to advance_payments. client_id retained.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_add_client_record_id_to_advance_payments"
down_revision: Union[str, None] = "0006_add_client_record_id_to_binders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "advance_payments",
        sa.Column("client_record_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_advance_payments_client_record_id",
        "advance_payments",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index(
        "ix_advance_payments_client_record_id",
        "advance_payments",
        ["client_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_advance_payments_client_record_id", table_name="advance_payments")
    op.drop_constraint("fk_advance_payments_client_record_id", "advance_payments", type_="foreignkey")
    op.drop_column("advance_payments", "client_record_id")
