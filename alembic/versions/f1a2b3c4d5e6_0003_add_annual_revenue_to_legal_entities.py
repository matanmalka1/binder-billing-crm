"""add_annual_revenue_to_legal_entities

Adds annual_revenue column to legal_entities for storing the client's annual
business turnover. Used for display and advisory purposes only.

Revision ID: f1a2b3c4d5e6
Revises: ea56adf8adb6
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'ea56adf8adb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'legal_entities',
        sa.Column('annual_revenue', sa.Numeric(15, 0), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('legal_entities', 'annual_revenue')
