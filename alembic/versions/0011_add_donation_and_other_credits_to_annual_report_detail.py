"""add donation_amount and other_credits to annual_report_details

Revision ID: 0011_add_donation_and_other_credits_to_annual_report_detail
Revises: 0010_add_pension_contribution_to_annual_report_detail
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_add_donation_and_other_credits_to_annual_report_detail"
down_revision = "0010_add_pension_contribution_to_annual_report_detail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_report_details",
        sa.Column("donation_amount", sa.Numeric(12, 2), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_report_details",
        sa.Column("other_credits", sa.Numeric(12, 2), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("annual_report_details", "other_credits")
    op.drop_column("annual_report_details", "donation_amount")
