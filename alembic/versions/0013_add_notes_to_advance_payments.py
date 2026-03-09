"""add notes to advance_payments

Revision ID: 0013_add_notes_to_advance_payments
Revises: 0012_add_tax_year_to_permanent_documents
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_add_notes_to_advance_payments"
down_revision = "0012_add_tax_year_to_permanent_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "advance_payments",
        sa.Column("notes", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("advance_payments", "notes")
