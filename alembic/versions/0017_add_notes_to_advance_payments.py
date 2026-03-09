"""add notes to advance_payments

Revision ID: 0017
Revises: 0016
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "advance_payments",
        sa.Column("notes", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("advance_payments", "notes")
