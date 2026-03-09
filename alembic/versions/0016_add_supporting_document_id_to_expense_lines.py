"""add supporting_document_id to annual_report_expense_lines

Revision ID: 0016_add_supporting_document_id_to_expense_lines
Revises: 0015_add_tax_year_to_permanent_documents
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_add_supporting_document_id_to_expense_lines"
down_revision = "0015_add_tax_year_to_permanent_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
