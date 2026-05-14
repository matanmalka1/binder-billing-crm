"""alter task due_date from DateTime to Date

Revision ID: 0004_task_due_date_to_date
Revises: 0003_task_canceled_by_user_id
Create Date: 2026-05-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_task_due_date_to_date"
down_revision: Union[str, Sequence[str], None] = "0003_task_canceled_by_user_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "tasks",
            "due_date",
            type_=sa.Date(),
            existing_type=sa.DateTime(),
            existing_nullable=True,
            postgresql_using="due_date::date",
        )
    else:
        with op.batch_alter_table("tasks") as batch_op:
            batch_op.alter_column(
                "due_date",
                type_=sa.Date(),
                existing_type=sa.DateTime(),
                existing_nullable=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "tasks",
            "due_date",
            type_=sa.DateTime(),
            existing_type=sa.Date(),
            existing_nullable=True,
            postgresql_using="due_date::timestamp",
        )
    else:
        with op.batch_alter_table("tasks") as batch_op:
            batch_op.alter_column(
                "due_date",
                type_=sa.DateTime(),
                existing_type=sa.Date(),
                existing_nullable=True,
            )
