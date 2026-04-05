"""set paid_amount non-nullable with default 0 on advance_payments

Revision ID: 71ead2aae8c6
Revises: 214426106435
Create Date: 2026-04-05 15:15:45.497039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71ead2aae8c6'
down_revision: Union[str, Sequence[str], None] = '214426106435'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill NULLs before enforcing NOT NULL
    op.execute("UPDATE advance_payments SET paid_amount = 0 WHERE paid_amount IS NULL")
    with op.batch_alter_table('advance_payments') as batch_op:
        batch_op.alter_column('paid_amount',
            existing_type=sa.NUMERIC(precision=10, scale=2),
            nullable=False,
            server_default="0")


def downgrade() -> None:
    with op.batch_alter_table('advance_payments') as batch_op:
        batch_op.alter_column('paid_amount',
            existing_type=sa.NUMERIC(precision=10, scale=2),
            nullable=True,
            server_default=None)
