"""add is_full to binders

Revision ID: 4c9d2e3b1f6a
Revises: 3b7e2c1a0f5d
Create Date: 2026-03-24

Adds is_full boolean flag to binders. A full binder stays IN_OFFICE but is
excluded from the active-binder uniqueness index so a new binder can be opened
for the same client with the same binder_number.
"""

from alembic import op
import sqlalchemy as sa

revision = "4c9d2e3b1f6a"
down_revision = "3b7e2c1a0f5d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("binders", sa.Column("is_full", sa.Boolean(), nullable=False, server_default=sa.false()))

    # Drop the old unique index (no is_full condition) and recreate it
    # excluding full binders so two binders with the same number can coexist
    # when the older one is marked full.
    op.drop_index("idx_active_binder_unique", table_name="binders")
    op.create_index(
        "idx_active_binder_unique",
        "binders",
        ["binder_number"],
        unique=True,
        postgresql_where=sa.text("status != 'returned' AND deleted_at IS NULL AND is_full = false"),
        sqlite_where=sa.text("status != 'returned' AND deleted_at IS NULL AND is_full = 0"),
    )


def downgrade() -> None:
    op.drop_index("idx_active_binder_unique", table_name="binders")
    op.create_index(
        "idx_active_binder_unique",
        "binders",
        ["binder_number"],
        unique=True,
        postgresql_where=sa.text("status != 'returned' AND deleted_at IS NULL"),
        sqlite_where=sa.text("status != 'returned' AND deleted_at IS NULL"),
    )
    op.drop_column("binders", "is_full")
