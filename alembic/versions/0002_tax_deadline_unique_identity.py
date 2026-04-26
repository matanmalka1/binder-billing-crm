"""tax_deadline_unique_identity

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-26 12:00:00.000000

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0002
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0001

Notes:
- Adds DB-level uniqueness for active tax deadline identity.
- Applies only to period-based deadlines (`period IS NOT NULL`).
- Existing duplicate active rows must be resolved before upgrade if present.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_tax_deadline_active_period_identity",
        "tax_deadlines",
        ["client_record_id", "deadline_type", "period"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND period IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_tax_deadline_active_period_identity",
        table_name="tax_deadlines",
        postgresql_where=sa.text("deleted_at IS NULL AND period IS NOT NULL"),
    )
