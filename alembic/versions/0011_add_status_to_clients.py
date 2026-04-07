"""add_status_to_clients

Revision ID: 9b225dd8ca06
Revises: b2c3d4e5f6a7
Create Date: 2026-04-07 14:15:13.560173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b225dd8ca06'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'clients',
        sa.Column(
            'status',
            sa.String(length=10),
            nullable=False,
            server_default='active',
        ),
    )


def downgrade() -> None:
    op.drop_column('clients', 'status')
