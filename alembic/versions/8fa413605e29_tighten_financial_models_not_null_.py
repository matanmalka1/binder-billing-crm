"""tighten financial models: NOT NULL expected/calculated; SoftDeletableMixin

Revision ID: 8fa413605e29
Revises: 0002_add_overview_query_indexes
Create Date: 2026-05-19 11:59:51.170720

Notes:
    turnover_amount and advance_rate are source snapshots — NULL means "missing /
    unknown source data" and must remain nullable. Only the derived display
    columns expected_amount and calculated_amount are tightened to NOT NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fa413605e29'
down_revision: Union[str, Sequence[str], None] = '0002_add_overview_query_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('advance_payments', sa.Column('restored_at', sa.DateTime(), nullable=True))
    op.add_column('advance_payments', sa.Column('restored_by', sa.Integer(), nullable=True))

    # Backfill NULL → 0 only for derived display columns.
    # turnover_amount and advance_rate keep NULL semantics for missing snapshots.
    op.execute(
        sa.text(
            "UPDATE advance_payments SET "
            "expected_amount = COALESCE(expected_amount, 0), "
            "calculated_amount = COALESCE(calculated_amount, 0) "
            "WHERE expected_amount IS NULL OR calculated_amount IS NULL"
        )
    )

    op.alter_column('advance_payments', 'expected_amount',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               nullable=False)
    op.alter_column('advance_payments', 'calculated_amount',
               existing_type=sa.NUMERIC(precision=12, scale=2),
               nullable=False)
    op.create_foreign_key(
        'fk_advance_payments_restored_by_users',
        'advance_payments', 'users',
        ['restored_by'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_advance_payments_restored_by_users', 'advance_payments', type_='foreignkey')
    op.alter_column('advance_payments', 'calculated_amount',
               existing_type=sa.NUMERIC(precision=12, scale=2),
               nullable=True)
    op.alter_column('advance_payments', 'expected_amount',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               nullable=True)
    op.drop_column('advance_payments', 'restored_by')
    op.drop_column('advance_payments', 'restored_at')
