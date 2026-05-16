"""drop notification read state

Revision ID: 0008_drop_notification_read_state
Revises: 0007_remove_signature_request_draft
Create Date: 2026-05-16 00:00:00.000000

Run:
- Upgrade:   APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic upgrade 0008_drop_notification_read_state
- Downgrade: APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic downgrade 0007_remove_signature_request_draft

Notes:
- Notifications are outbound delivery records, not an inbox.
- Drops is_read (Boolean non-null) and read_at (DateTime nullable) columns.
- Downgrade restores is_read with server_default=false backfill, then removes the default
  to match the original schema (non-null, no server default).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_drop_notification_read_state"
down_revision: Union[str, Sequence[str], None] = "0007_remove_signature_request_draft"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("notifications", "is_read")
    op.drop_column("notifications", "read_at")


def downgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("read_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column("notifications", "is_read", server_default=None)
