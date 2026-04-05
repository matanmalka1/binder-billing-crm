"""fix vat_work_item unique constraint with partial index for soft delete

Revision ID: 214426106435
Revises: 6e3f2b1d0c8a
Create Date: 2026-04-05 15:12:39.079999

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '214426106435'
down_revision: Union[str, Sequence[str], None] = '6e3f2b1d0c8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('vat_work_items') as batch_op:
        batch_op.drop_constraint('uq_vat_work_item_business_period', type_='unique')
    op.create_index('uq_vat_work_item_business_period', 'vat_work_items', ['business_id', 'period'], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    op.drop_index('uq_vat_work_item_business_period', table_name='vat_work_items', postgresql_where=sa.text('deleted_at IS NULL'))
    with op.batch_alter_table('vat_work_items') as batch_op:
        batch_op.create_unique_constraint('uq_vat_work_item_business_period', ['business_id', 'period'])
