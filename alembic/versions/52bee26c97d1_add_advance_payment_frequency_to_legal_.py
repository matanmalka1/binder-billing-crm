"""add advance_payment_frequency to legal_entities

Revision ID: 52bee26c97d1
Revises: c4d6e8f10203
Create Date: 2026-05-04 23:28:24.593575

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '52bee26c97d1'
down_revision: Union[str, Sequence[str], None] = 'c4d6e8f10203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_advance_payment_frequency_enum = sa.Enum(
    'monthly', 'bimonthly',
    name='advance_payment_frequency',
    create_type=True,
)


def upgrade() -> None:
    _advance_payment_frequency_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'legal_entities',
        sa.Column('advance_payment_frequency', _advance_payment_frequency_enum, nullable=True),
    )


def downgrade() -> None:
    op.drop_column('legal_entities', 'advance_payment_frequency')
    _advance_payment_frequency_enum.drop(op.get_bind(), checkfirst=True)
