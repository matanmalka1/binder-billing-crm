"""drop clients table

Revision ID: 00fa037f8cb3
Revises: 1d7068742798
Create Date: 2026-04-20 17:53:31.759981

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 00fa037f8cb3
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 1d7068742798

Notes:
- Drops the legacy clients table after all runtime paths moved to ClientRecord + LegalEntity + Person.
- Keeps downgrade explicit by recreating the legacy table and its partial indexes.
- No data backfill is attempted on downgrade.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00fa037f8cb3'
down_revision: Union[str, Sequence[str], None] = '1d7068742798'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('clients')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('id_number', sa.String(), nullable=False),
        sa.Column('id_number_type', sa.Enum('INDIVIDUAL', 'CORPORATION', 'PASSPORT', 'OTHER', name='idnumbertype'), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('address_street', sa.String(), nullable=True),
        sa.Column('address_building_number', sa.String(), nullable=True),
        sa.Column('address_apartment', sa.String(), nullable=True),
        sa.Column('address_city', sa.String(), nullable=True),
        sa.Column('address_zip_code', sa.String(), nullable=True),
        sa.Column('entity_type', sa.Enum('OSEK_PATUR', 'OSEK_MURSHE', 'COMPANY_LTD', 'EMPLOYEE', name='entitytype'), nullable=True),
        sa.Column('vat_reporting_frequency', sa.Enum('MONTHLY', 'BIMONTHLY', 'EXEMPT', name='vattype'), nullable=True),
        sa.Column('vat_exempt_ceiling', sa.Numeric(precision=12, scale=0), nullable=True),
        sa.Column('advance_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('advance_rate_updated_at', sa.Date(), nullable=True),
        sa.Column('accountant_name', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'FROZEN', 'CLOSED', name='clientstatus'), nullable=False),
        sa.Column('office_client_number', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('restored_at', sa.DateTime(), nullable=True),
        sa.Column('restored_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['restored_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_clients_full_name', 'clients', ['full_name'], unique=False)
    op.create_index(
        'ix_clients_id_number_active',
        'clients',
        ['id_number'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
        sqlite_where=sa.text('deleted_at IS NULL'),
    )
    op.create_index(
        'ix_clients_office_client_number_active',
        'clients',
        ['office_client_number'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
        sqlite_where=sa.text('deleted_at IS NULL'),
    )
