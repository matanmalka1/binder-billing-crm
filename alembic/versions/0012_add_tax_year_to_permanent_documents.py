"""add tax_year to permanent_documents

Revision ID: 0012_add_tax_year_to_permanent_documents
Revises: 0011_add_columns_to_expense_lines
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_add_tax_year_to_permanent_documents"
down_revision = "0011_add_columns_to_expense_lines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "permanent_documents",
        sa.Column("tax_year", sa.SmallInteger(), nullable=True),
    )
    op.create_index(
        "ix_permanent_documents_tax_year",
        "permanent_documents",
        ["tax_year"],
    )


def downgrade() -> None:
    op.drop_index("ix_permanent_documents_tax_year", table_name="permanent_documents")
    op.drop_column("permanent_documents", "tax_year")
