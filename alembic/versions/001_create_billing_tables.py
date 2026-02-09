"""create charges and invoices tables

Revision ID: 001_sprint3_billing
Revises: 
Create Date: 2026-02-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_sprint3_billing'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create charges and invoices tables for Sprint 3 billing module."""
    
    # Create charges table
    op.create_table(
        'charges',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='ILS'),
        sa.Column('charge_type', sa.Enum('retainer', 'one_time', name='chargetype'), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=True),
        sa.Column('status', sa.Enum('draft', 'issued', 'paid', 'canceled', name='chargestatus'), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('issued_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_charges_client_id'), 'charges', ['client_id'], unique=False)
    
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('charge_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('external_invoice_id', sa.String(), nullable=False),
        sa.Column('document_url', sa.String(), nullable=True),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['charge_id'], ['charges.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('charge_id')
    )
    op.create_index(op.f('ix_invoices_charge_id'), 'invoices', ['charge_id'], unique=False)


def downgrade() -> None:
    """Drop charges and invoices tables."""
    
    op.drop_index(op.f('ix_invoices_charge_id'), table_name='invoices')
    op.drop_table('invoices')
    
    op.drop_index(op.f('ix_charges_client_id'), table_name='charges')
    op.drop_table('charges')
    
    bind = op.get_bind()
    sa.Enum(name='chargestatus').drop(bind, checkfirst=True)
    sa.Enum(name='chargetype').drop(bind, checkfirst=True)
