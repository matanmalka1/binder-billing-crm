"""add advance payment period active index

Revision ID: 0006_add_advance_payment_period_active_index
Revises: 0005_reorder_vat_turnover_lookup_index
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_add_advance_payment_period_active_index"
down_revision: Union[str, Sequence[str], None] = "0005_reorder_vat_turnover_lookup_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    op.create_index(
        "idx_advance_payment_period_active",
        "advance_payments",
        ["period"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )


def downgrade() -> None:
    op.drop_index("idx_advance_payment_period_active", table_name="advance_payments")
