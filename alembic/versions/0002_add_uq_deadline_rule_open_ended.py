"""Add partial unique index: one open-ended DeadlineRule per rule_type.

Revision ID: 0002_add_uq_deadline_rule_open_ended
Revises: dde4169a5aca
Create Date: 2026-05-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_add_uq_deadline_rule_open_ended"
down_revision = "dde4169a5aca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_deadline_rule_open_ended "
            "ON deadline_rules (rule_type) WHERE effective_to IS NULL"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute(sa.text("DROP INDEX IF EXISTS uq_deadline_rule_open_ended"))
