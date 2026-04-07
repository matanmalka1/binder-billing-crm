"""add_vat_reporting_frequency_to_clients

Revision ID: c2d3e4f5a6b7
Revises: 9b225dd8ca06
Create Date: 2026-04-07 18:00:00.000000

Adds vat_reporting_frequency to the clients table.
This field is the authoritative VAT reporting frequency for OSEK_MURSHE businesses
under this client. COMPANY businesses continue using BusinessTaxProfile.vat_type.
NULL means not yet configured; the service layer defaults to BIMONTHLY for OSEK_MURSHE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = '9b225dd8ca06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'clients',
        sa.Column('vat_reporting_frequency', sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('clients', 'vat_reporting_frequency')
