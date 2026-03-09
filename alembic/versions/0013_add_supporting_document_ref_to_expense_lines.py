"""add supporting_document_ref to annual_report_expense_lines

Revision ID: 0013_add_supporting_document_ref_to_expense_lines
Revises: 0012_add_recognition_rate_to_expense_lines
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_add_supporting_document_ref_to_expense_lines"
down_revision = "0012_add_recognition_rate_to_expense_lines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_report_expense_lines",
        sa.Column("supporting_document_ref", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("annual_report_expense_lines", "supporting_document_ref")
