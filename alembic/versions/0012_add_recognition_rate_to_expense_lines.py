"""add recognition_rate to annual_report_expense_lines

Revision ID: 0012_add_recognition_rate_to_expense_lines
Revises: 0011_add_donation_and_other_credits_to_annual_report_detail
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_add_recognition_rate_to_expense_lines"
down_revision = "0011_add_donation_and_other_credits_to_annual_report_detail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_report_expense_lines",
        sa.Column(
            "recognition_rate",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="1.00",
        ),
    )
    # Apply statutory rates for existing rows
    op.execute(
        "UPDATE annual_report_expense_lines SET recognition_rate = 0.75 WHERE category = 'vehicle'"
    )
    op.execute(
        "UPDATE annual_report_expense_lines SET recognition_rate = 0.80 WHERE category = 'communication'"
    )


def downgrade() -> None:
    op.drop_column("annual_report_expense_lines", "recognition_rate")
