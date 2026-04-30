"""reminder tax deadline identity

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-30 10:15:00

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0006
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0005

Notes:
- Keeps one active generic reminder per client/type/date when no tax deadline is linked.
- Allows different tax deadlines on the same date to each have their own reminder.
- Downgrade can fail if active tax-deadline reminders now conflict under the old identity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE_UNLINKED = "status != 'canceled' AND deleted_at IS NULL AND tax_deadline_id IS NULL"
ACTIVE_TAX_DEADLINE = "status != 'canceled' AND deleted_at IS NULL AND tax_deadline_id IS NOT NULL"
ACTIVE_OLD = "status != 'canceled' AND deleted_at IS NULL"


def upgrade() -> None:
    op.drop_index("uq_reminder_active", table_name="reminders")
    op.create_index(
        "uq_reminder_active",
        "reminders",
        ["client_record_id", "reminder_type", "target_date"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_UNLINKED),
        sqlite_where=sa.text(ACTIVE_UNLINKED),
    )
    op.create_index(
        "uq_reminder_tax_deadline_active",
        "reminders",
        ["tax_deadline_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_TAX_DEADLINE),
        sqlite_where=sa.text(ACTIVE_TAX_DEADLINE),
    )


def downgrade() -> None:
    op.drop_index("uq_reminder_tax_deadline_active", table_name="reminders")
    op.drop_index("uq_reminder_active", table_name="reminders")
    op.create_index(
        "uq_reminder_active",
        "reminders",
        ["client_record_id", "reminder_type", "target_date"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_OLD),
        sqlite_where=sa.text(ACTIVE_OLD),
    )
