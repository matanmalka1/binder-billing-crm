"""add pension_contribution to annual_report_details

Revision ID: 0010_add_pension_contribution_to_annual_report_detail
Revises: 0009_add_annual_report_annex_data
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_add_pension_contribution_to_annual_report_detail"
down_revision = "0009_add_annual_report_annex_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_report_details",
        sa.Column("pension_contribution", sa.Numeric(12, 2), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("annual_report_details", "pension_contribution")
