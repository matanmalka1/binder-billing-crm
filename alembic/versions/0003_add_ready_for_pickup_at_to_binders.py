"""add_ready_for_pickup_at_to_binders

Revision ID: 966f3c2d3267
Revises: 0002
Create Date: 2026-04-28 14:00:49.282411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '966f3c2d3267'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('binders', sa.Column('ready_for_pickup_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('binders', 'ready_for_pickup_at')
