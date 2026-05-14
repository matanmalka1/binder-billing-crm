"""add canceled_by_user_id to tasks

Revision ID: 0003_task_canceled_by_user_id
Revises: 0002_remove_task_in_progress_status
Create Date: 2026-05-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_task_canceled_by_user_id"
down_revision: Union[str, Sequence[str], None] = "0002_remove_task_in_progress_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "canceled_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tasks", "canceled_by_user_id")
