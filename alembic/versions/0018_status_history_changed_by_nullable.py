"""status_history_changed_by_nullable

Allow system-generated status history rows (created by obligation orchestrator
without a human actor) by making changed_by nullable.

Revision ID: 0018_status_history_changed_by_nullable
Revises: 0017_annual_report_created_by_nullable
Create Date: 2026-04-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_status_history_changed_by_nullable"
down_revision: Union[str, None] = "0017_annual_report_created_by_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("annual_report_status_history") as batch_op:
        batch_op.alter_column(
            "changed_by",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    # Rows with NULL changed_by will block the NOT NULL restore — handle manually.
    with op.batch_alter_table("annual_report_status_history") as batch_op:
        batch_op.alter_column(
            "changed_by",
            existing_type=sa.Integer(),
            nullable=False,
        )
