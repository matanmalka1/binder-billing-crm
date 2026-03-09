"""add recognition_rate, supporting_document_ref, and supporting_document_id to annual_report_expense_lines

Revision ID: 0011_add_columns_to_expense_lines
Revises: 0010_add_columns_to_annual_report_details
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_add_columns_to_expense_lines"
down_revision = "0010_add_columns_to_annual_report_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_report_expense_lines",
        sa.Column("recognition_rate", sa.Numeric(5, 2), nullable=False, server_default="1.00"),
    )
    # Apply statutory rates for existing rows
    op.execute(
        "UPDATE annual_report_expense_lines SET recognition_rate = 0.75 WHERE category = 'vehicle'"
    )
    op.execute(
        "UPDATE annual_report_expense_lines SET recognition_rate = 0.80 WHERE category = 'communication'"
    )
    op.add_column(
        "annual_report_expense_lines",
        sa.Column("supporting_document_ref", sa.String(255), nullable=True),
    )
    op.add_column(
        "annual_report_expense_lines",
        sa.Column("supporting_document_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_expense_lines_supporting_document",
        "annual_report_expense_lines",
        "permanent_documents",
        ["supporting_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_annual_report_expense_lines_supporting_document_id",
        "annual_report_expense_lines",
        ["supporting_document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_annual_report_expense_lines_supporting_document_id",
        table_name="annual_report_expense_lines",
    )
    op.drop_constraint(
        "fk_expense_lines_supporting_document",
        "annual_report_expense_lines",
        type_="foreignkey",
    )
    op.drop_column("annual_report_expense_lines", "supporting_document_id")
    op.drop_column("annual_report_expense_lines", "supporting_document_ref")
    op.drop_column("annual_report_expense_lines", "recognition_rate")
