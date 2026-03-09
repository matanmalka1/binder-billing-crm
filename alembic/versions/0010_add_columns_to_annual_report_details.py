"""add credit_point and financial columns to annual_report_details

Revision ID: 0010_add_columns_to_annual_report_details
Revises: 0009_add_annual_report_annex_data
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_add_columns_to_annual_report_details"
down_revision = "0009_add_annual_report_annex_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_report_details",
        sa.Column("pension_contribution", sa.Numeric(12, 2), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_report_details",
        sa.Column("donation_amount", sa.Numeric(12, 2), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_report_details",
        sa.Column("other_credits", sa.Numeric(12, 2), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_report_details",
        sa.Column("pension_credit_points", sa.Numeric(5, 2), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_report_details",
        sa.Column("life_insurance_credit_points", sa.Numeric(5, 2), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_report_details",
        sa.Column("tuition_credit_points", sa.Numeric(5, 2), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("annual_report_details", "tuition_credit_points")
    op.drop_column("annual_report_details", "life_insurance_credit_points")
    op.drop_column("annual_report_details", "pension_credit_points")
    op.drop_column("annual_report_details", "other_credits")
    op.drop_column("annual_report_details", "donation_amount")
    op.drop_column("annual_report_details", "pension_contribution")
