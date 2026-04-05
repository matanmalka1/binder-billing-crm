"""add expiry_days to signature_requests

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-05 00:00:01.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('signature_requests') as batch_op:
        batch_op.add_column(
            sa.Column('expiry_days', sa.Integer(), nullable=False, server_default='14')
        )


def downgrade() -> None:
    with op.batch_alter_table('signature_requests') as batch_op:
        batch_op.drop_column('expiry_days')
