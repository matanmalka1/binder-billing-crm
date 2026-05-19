"""add client records active created index

Revision ID: 0004_add_client_records_active_created_index
Revises: 0003_add_vat_turnover_lookup_index
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_add_client_records_active_created_index"
down_revision: Union[str, Sequence[str], None] = "0003_add_vat_turnover_lookup_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    op.create_index(
        "ix_client_records_active_created_desc",
        "client_records",
        [sa.text("created_at DESC")],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )


def downgrade() -> None:
    op.drop_index("ix_client_records_active_created_desc", table_name="client_records")
