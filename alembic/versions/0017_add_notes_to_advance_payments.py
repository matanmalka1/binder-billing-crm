"""add notes to advance_payments

Revision ID: 0017_add_notes_to_advance_payments
Revises: 0016_add_supporting_document_id_to_expense_lines
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_add_notes_to_advance_payments"
down_revision = "0016_add_supporting_document_id_to_expense_lines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "advance_payments",
        sa.Column("notes", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("advance_payments", "notes")
