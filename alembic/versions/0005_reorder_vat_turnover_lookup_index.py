"""reorder vat turnover lookup index

Revision ID: 0005_reorder_vat_turnover_lookup_index
Revises: 0004_add_client_records_active_created_index
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_reorder_vat_turnover_lookup_index"
down_revision: Union[str, Sequence[str], None] = "0004_add_client_records_active_created_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    op.drop_index("ix_vat_work_items_turnover_lookup", table_name="vat_work_items")
    op.create_index(
        "ix_vat_work_items_turnover_lookup",
        "vat_work_items",
        ["client_record_id", "period", "status"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )


def downgrade() -> None:
    op.drop_index("ix_vat_work_items_turnover_lookup", table_name="vat_work_items")
    op.create_index(
        "ix_vat_work_items_turnover_lookup",
        "vat_work_items",
        ["client_record_id", "status", "period"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )
