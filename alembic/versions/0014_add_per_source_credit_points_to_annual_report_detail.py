"""add per-source credit point fields to annual_report_details

Revision ID: 0014_add_per_source_credit_points_to_annual_report_detail
Revises: 0013_add_supporting_document_ref_to_expense_lines
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_add_per_source_credit_points_to_annual_report_detail"
down_revision = "0013_add_supporting_document_ref_to_expense_lines"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
