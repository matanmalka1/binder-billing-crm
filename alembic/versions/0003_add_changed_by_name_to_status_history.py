"""add changed_by_name to annual_report_status_history

Revision ID: 3b7e2c1a0f5d
Revises: 8a3c1f2b9d4e
Create Date: 2026-03-24

Stores the display name of the user who made each status change so that
history responses can return it without a join to the users table.
"""

from alembic import op
import sqlalchemy as sa

revision = "3b7e2c1a0f5d"
down_revision = "8a3c1f2b9d4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_report_status_history",
        sa.Column("changed_by_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("annual_report_status_history", "changed_by_name")
