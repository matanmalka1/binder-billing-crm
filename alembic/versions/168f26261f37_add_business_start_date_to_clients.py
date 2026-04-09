"""add_business_start_date_to_clients

Revision ID: 168f26261f37
Revises: f5a6b7c8d9e0
Create Date: 2026-04-09 12:56:25.627725

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '168f26261f37'
down_revision: Union[str, Sequence[str], None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('business_start_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'business_start_date')
