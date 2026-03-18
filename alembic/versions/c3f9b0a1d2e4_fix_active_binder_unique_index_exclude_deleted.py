"""fix active binder unique index exclude deleted

Revision ID: c3f9b0a1d2e4
Revises: a7529d8677dc
Create Date: 2026-03-18 12:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f9b0a1d2e4"
down_revision: Union[str, Sequence[str], None] = "a7529d8677dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_active_binder_unique", table_name="binders")
    op.create_index(
        "idx_active_binder_unique",
        "binders",
        ["binder_number"],
        unique=True,
        postgresql_where=sa.text("status != 'returned' AND deleted_at IS NULL"),
        sqlite_where=sa.text("status != 'returned' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_active_binder_unique", table_name="binders")
    op.create_index(
        "idx_active_binder_unique",
        "binders",
        ["binder_number"],
        unique=True,
        postgresql_where=sa.text("status != 'returned'"),
        sqlite_where=sa.text("status != 'returned'"),
    )
