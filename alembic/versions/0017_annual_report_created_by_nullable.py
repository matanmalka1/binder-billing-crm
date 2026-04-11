"""annual_report_created_by_nullable

Allow system-generated annual report shells (created by obligation orchestrator
without a human actor) by making created_by nullable.

Revision ID: 0017_annual_report_created_by_nullable
Revises: 5a9255230515
Create Date: 2026-04-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_annual_report_created_by_nullable"
down_revision: Union[str, None] = "5a9255230515"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.alter_column(
            "created_by",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    # Rows with NULL created_by will block the NOT NULL restore — handle manually.
    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.alter_column(
            "created_by",
            existing_type=sa.Integer(),
            nullable=False,
        )
