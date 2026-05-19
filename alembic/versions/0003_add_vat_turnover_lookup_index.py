"""add vat turnover lookup index

Revision ID: 0003_add_vat_turnover_lookup_index
Revises: 9a111db38eba
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_add_vat_turnover_lookup_index"
down_revision: Union[str, Sequence[str], None] = "9a111db38eba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    op.create_index(
        "ix_vat_work_items_turnover_lookup",
        "vat_work_items",
        ["client_record_id", "status", "period"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )


def downgrade() -> None:
    op.drop_index("ix_vat_work_items_turnover_lookup", table_name="vat_work_items")
