"""add composite partial index on vat_work_items(due_date_effective, client_record_id)

Revision ID: 0003_vat_due_date_client_index
Revises: 0002_password_reset_tokens
Create Date: 2026-05-27

Supports:
- list_by_due_date_paginated:
    WHERE deleted_at IS NULL AND due_date_effective = :date
    ORDER BY client_record_id ASC
- list_due_date_groups:
    full scan over active VAT items grouped by due_date_effective
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_vat_due_date_client_index"
down_revision: Union[str, Sequence[str], None] = "0002_password_reset_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_vat_work_items_active_due_client",
        "vat_work_items",
        ["due_date_effective", "client_record_id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_vat_work_items_active_due_client",
        table_name="vat_work_items",
    )
