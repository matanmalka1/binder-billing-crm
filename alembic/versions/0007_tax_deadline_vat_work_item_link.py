"""tax deadline vat work item link

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-30 16:30:00

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0007
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0006

Notes:
- Adds tax_deadlines.vat_work_item_id for direct navigation from VAT deadlines.
- Backfills existing VAT deadlines by client_record_id + period where a work item exists.
- PostgreSQL and SQLite both use a nullable FK plus a partial unique index.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE_LINK = "deleted_at IS NULL AND vat_work_item_id IS NOT NULL"


def upgrade() -> None:
    op.add_column("tax_deadlines", sa.Column("vat_work_item_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tax_deadlines_vat_work_item_id_vat_work_items",
        "tax_deadlines",
        "vat_work_items",
        ["vat_work_item_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_tax_deadline_vat_work_item_link",
        "tax_deadlines",
        "(vat_work_item_id IS NULL) OR (deadline_type = 'vat')",
    )
    op.create_index(
        "ix_tax_deadlines_vat_work_item_id",
        "tax_deadlines",
        ["vat_work_item_id"],
    )
    op.create_index(
        "uq_tax_deadline_vat_work_item_active",
        "tax_deadlines",
        ["vat_work_item_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_LINK),
        sqlite_where=sa.text(ACTIVE_LINK),
    )
    op.execute(
        sa.text(
            """
            UPDATE tax_deadlines AS td
            SET vat_work_item_id = vwi.id
            FROM vat_work_items AS vwi
            WHERE td.deadline_type = 'vat'
              AND td.deleted_at IS NULL
              AND vwi.deleted_at IS NULL
              AND td.vat_work_item_id IS NULL
              AND td.client_record_id = vwi.client_record_id
              AND td.period = vwi.period
            """
        )
    )


def downgrade() -> None:
    op.drop_index("uq_tax_deadline_vat_work_item_active", table_name="tax_deadlines")
    op.drop_index("ix_tax_deadlines_vat_work_item_id", table_name="tax_deadlines")
    op.drop_constraint("ck_tax_deadline_vat_work_item_link", "tax_deadlines", type_="check")
    op.drop_constraint(
        "fk_tax_deadlines_vat_work_item_id_vat_work_items",
        "tax_deadlines",
        type_="foreignkey",
    )
    op.drop_column("tax_deadlines", "vat_work_item_id")
