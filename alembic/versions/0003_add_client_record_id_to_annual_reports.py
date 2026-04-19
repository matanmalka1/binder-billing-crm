"""add_client_record_id_to_annual_reports

Revision ID: 0003_add_client_record_id_to_annual_reports
Revises: 0002_add_legal_entity_id_to_businesses
Create Date: 2026-04-19

Additive only: adds client_record_id FK to annual_reports. client_id retained.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_add_client_record_id_to_annual_reports"
down_revision: Union[str, None] = "0002_add_legal_entity_id_to_businesses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "annual_reports",
        sa.Column("client_record_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_annual_reports_client_record_id",
        "annual_reports",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index(
        "ix_annual_reports_client_record_id",
        "annual_reports",
        ["client_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_annual_reports_client_record_id", table_name="annual_reports")
    op.drop_constraint("fk_annual_reports_client_record_id", "annual_reports", type_="foreignkey")
    op.drop_column("annual_reports", "client_record_id")
