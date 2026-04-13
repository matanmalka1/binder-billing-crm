"""fix tax deadline advance payment check constraint

Revision ID: 0002_fix_tax_deadline_advance_payment_check_constraint
Revises: 0001_initial_schema
Create Date: 2026-04-13

Fixes the ck_tax_deadline_advance_payment_link constraint direction:
- Old: ADVANCE_PAYMENT deadlines must have advance_payment_id (blocks auto-generation)
- New: If advance_payment_id is set, deadline_type must be ADVANCE_PAYMENT (allows auto-generated deadlines without a linked payment)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002_fix_tax_deadline_advance_payment_check_constraint'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tax_deadlines', schema=None) as batch_op:
        batch_op.drop_constraint('ck_tax_deadline_advance_payment_link', type_='check')
        batch_op.create_check_constraint(
            'ck_tax_deadline_advance_payment_link',
            sa.text("(advance_payment_id IS NULL) OR (deadline_type = 'advance_payment')"),
        )


def downgrade() -> None:
    with op.batch_alter_table('tax_deadlines', schema=None) as batch_op:
        batch_op.drop_constraint('ck_tax_deadline_advance_payment_link', type_='check')
        batch_op.create_check_constraint(
            'ck_tax_deadline_advance_payment_link',
            sa.text("(deadline_type != 'advance_payment') OR (advance_payment_id IS NOT NULL)"),
        )
