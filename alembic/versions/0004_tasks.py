"""Add tasks table with TaskStatus and TaskPriority enums.

Revision ID: 0004_tasks
Revises: 0003_scheduler_reminders
Create Date: 2026-05-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_tasks"
down_revision = "0003_scheduler_reminders"
branch_labels = None
depends_on = None

_status = sa.Enum("open", "in_progress", "done", "canceled", name="taskstatus")
_priority = sa.Enum("low", "normal", "high", "urgent", name="taskpriority")


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _status, nullable=False, server_default="open"),
        sa.Column("priority", _priority, nullable=False, server_default="normal"),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_role", sa.String(length=50), nullable=True),
        sa.Column("source_domain", sa.String(length=100), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("action_key", sa.String(length=100), nullable=True),
        sa.Column("action_payload", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_tasks_status", "tasks", ["status"])
    op.create_index("idx_tasks_priority", "tasks", ["priority"])
    op.create_index("idx_tasks_due_date", "tasks", ["due_date"])
    op.create_index("idx_tasks_assigned_to_user_id", "tasks", ["assigned_to_user_id"])
    op.create_index("idx_tasks_source", "tasks", ["source_domain", "source_id"])


def downgrade() -> None:
    op.drop_index("idx_tasks_source", table_name="tasks")
    op.drop_index("idx_tasks_assigned_to_user_id", table_name="tasks")
    op.drop_index("idx_tasks_due_date", table_name="tasks")
    op.drop_index("idx_tasks_priority", table_name="tasks")
    op.drop_index("idx_tasks_status", table_name="tasks")
    op.drop_table("tasks")
    _priority.drop(op.get_bind(), checkfirst=True)
    _status.drop(op.get_bind(), checkfirst=True)
