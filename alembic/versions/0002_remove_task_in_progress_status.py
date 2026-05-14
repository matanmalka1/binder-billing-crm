"""remove task in_progress status

Revision ID: 0002_remove_task_in_progress_status
Revises: fc1eacc58833
Create Date: 2026-05-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002_remove_task_in_progress_status"
down_revision: Union[str, Sequence[str], None] = "fc1eacc58833"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_VALUES = ("open", "in_progress", "done", "canceled")
NEW_VALUES = ("open", "done", "canceled")


def upgrade() -> None:
    """Collapse in_progress tasks back to open and remove the enum value."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        result = bind.execute(sa.text(
            "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = 'taskstatus' AND e.enumlabel = 'in_progress'"
        ))
        if result.fetchone() is None:
            return
        op.execute(sa.text("UPDATE tasks SET status = 'open' WHERE status = 'in_progress'"))
        op.execute(sa.text("ALTER TYPE taskstatus RENAME TO taskstatus_old"))
        new_enum = postgresql.ENUM(*NEW_VALUES, name="taskstatus")
        new_enum.create(bind, checkfirst=False)
        op.execute(
            sa.text(
                "ALTER TABLE tasks ALTER COLUMN status TYPE taskstatus "
                "USING status::text::taskstatus"
            )
        )
        op.execute(sa.text("DROP TYPE taskstatus_old"))
        return

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(*OLD_VALUES, name="taskstatus"),
            type_=sa.Enum(*NEW_VALUES, name="taskstatus"),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Re-add the in_progress enum value for rollback compatibility."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TYPE taskstatus RENAME TO taskstatus_old"))
        old_enum = postgresql.ENUM(*OLD_VALUES, name="taskstatus")
        old_enum.create(bind, checkfirst=False)
        op.execute(
            sa.text(
                "ALTER TABLE tasks ALTER COLUMN status TYPE taskstatus "
                "USING status::text::taskstatus"
            )
        )
        op.execute(sa.text("DROP TYPE taskstatus_old"))
        return

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(*NEW_VALUES, name="taskstatus"),
            type_=sa.Enum(*OLD_VALUES, name="taskstatus"),
            existing_nullable=False,
        )
