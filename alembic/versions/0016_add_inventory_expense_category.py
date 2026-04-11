"""Add inventory VAT expense category.

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-04-09

Changes:
- Add 'inventory' to vatinvoice expense-category enum in PostgreSQL
- No schema change needed for SQLite (string-backed enums)
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "5a9255230515"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'inventory'")


def downgrade() -> None:
    # PostgreSQL enums cannot easily remove values in-place.
    # SQLite uses string-backed enums and requires no downgrade action.
    pass
