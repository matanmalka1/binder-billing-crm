"""advance_payments_remove_overdue_add_turnover_snapshot

Removes 'overdue' from advancepaymentstatus enum (overdue is now a computed
timing_status derived from due_date, not a stored value).
Migrates existing overdue rows to 'pending'.
Adds reported_turnover + turnover_source_vat_work_item_id for turnover snapshots.

Revision ID: ea56adf8adb6
Revises: e35ffb3fd002
Create Date: 2026-05-02 17:41:05.793128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ea56adf8adb6'
down_revision: Union[str, Sequence[str], None] = 'e35ffb3fd002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Migrate overdue rows to pending before touching the enum
    op.execute(
        "UPDATE advance_payments SET status = 'pending' WHERE status = 'overdue'"
    )

    # 2. Remove 'overdue' from the PostgreSQL enum type
    op.execute("ALTER TYPE advancepaymentstatus RENAME TO advancepaymentstatus_old")
    op.execute("CREATE TYPE advancepaymentstatus AS ENUM ('pending', 'paid', 'partial')")
    op.execute(
        "ALTER TABLE advance_payments "
        "ALTER COLUMN status TYPE advancepaymentstatus "
        "USING status::text::advancepaymentstatus"
    )
    op.execute("DROP TYPE advancepaymentstatus_old")

    # 3. Add turnover snapshot columns
    op.add_column('advance_payments', sa.Column('reported_turnover', sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column('advance_payments', sa.Column('turnover_source_vat_work_item_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_advance_payments_turnover_source_vat_work_item_id'),
        'advance_payments',
        ['turnover_source_vat_work_item_id'],
        unique=False,
    )
    op.create_foreign_key(
        'fk_advance_payments_turnover_source_vat_work_item',
        'advance_payments',
        'vat_work_items',
        ['turnover_source_vat_work_item_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_advance_payments_turnover_source_vat_work_item', 'advance_payments', type_='foreignkey')
    op.drop_index(op.f('ix_advance_payments_turnover_source_vat_work_item_id'), table_name='advance_payments')
    op.drop_column('advance_payments', 'turnover_source_vat_work_item_id')
    op.drop_column('advance_payments', 'reported_turnover')

    # Restore overdue to the enum (rows stay as pending — data loss is acceptable on downgrade)
    op.execute("ALTER TYPE advancepaymentstatus RENAME TO advancepaymentstatus_old")
    op.execute("CREATE TYPE advancepaymentstatus AS ENUM ('pending', 'paid', 'partial', 'overdue')")
    op.execute(
        "ALTER TABLE advance_payments "
        "ALTER COLUMN status TYPE advancepaymentstatus "
        "USING status::text::advancepaymentstatus"
    )
    op.execute("DROP TYPE advancepaymentstatus_old")
