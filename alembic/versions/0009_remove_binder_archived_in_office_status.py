"""remove binder archived in office status

Revision ID: 0009_remove_binder_archived_in_office_status
Revises: 0008_drop_notification_read_state
Create Date: 2026-05-17 00:00:00.000000

Run:
- Upgrade:   APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic upgrade 0009_remove_binder_archived_in_office_status
- Downgrade: APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic downgrade 0008_drop_notification_read_state

Notes:
- Replaces existing archived_in_office binder rows with closed_in_office.
- Recreates the PostgreSQL binderstatus enum without archived_in_office.
- Downgrade restores the enum value but does not infer which closed_in_office rows
  were previously archived_in_office.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_remove_binder_archived_in_office_status"
down_revision: Union[str, Sequence[str], None] = "0008_drop_notification_read_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_VALUES = (
    "in_office",
    "closed_in_office",
    "archived_in_office",
    "ready_for_pickup",
    "returned",
)
NEW_VALUES = (
    "in_office",
    "closed_in_office",
    "ready_for_pickup",
    "returned",
)


def _replace_postgres_enum(values: tuple[str, ...]) -> None:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    op.execute(sa.text(f"CREATE TYPE binderstatus_new AS ENUM ({quoted_values})"))
    op.execute(
        sa.text(
            "ALTER TABLE binders "
            "ALTER COLUMN status TYPE binderstatus_new "
            "USING status::text::binderstatus_new"
        )
    )
    op.execute(sa.text("DROP TYPE binderstatus"))
    op.execute(sa.text("ALTER TYPE binderstatus_new RENAME TO binderstatus"))


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(
        sa.text(
            "UPDATE binders "
            "SET status = 'closed_in_office' "
            "WHERE status = 'archived_in_office'"
        )
    )
    if bind.dialect.name == "postgresql":
        _replace_postgres_enum(NEW_VALUES)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _replace_postgres_enum(OLD_VALUES)
