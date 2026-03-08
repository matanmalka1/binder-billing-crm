"""add updated_at to clients

Revision ID: 0005_add_updated_at_to_clients
Revises: 0004_add_correspondence_entries_table
Create Date: 2026-03-08 10:30:20.542044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_add_updated_at_to_clients'
down_revision: Union[str, Sequence[str], None] = '0004_correspondence_entries'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'updated_at')
