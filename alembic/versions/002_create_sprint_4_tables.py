"""create notifications and permanent_documents tables

Revision ID: 002_sprint4_notifications
Revises: 001_sprint3_billing
Create Date: 2026-02-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_sprint4_notifications'
down_revision: Union[str, None] = '001_sprint3_billing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create notifications and permanent_documents tables for Sprint 4."""
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('binder_id', sa.Integer(), nullable=True),
        sa.Column('trigger', sa.Enum('binder_received', 'binder_approaching_sla', 'binder_overdue', 'binder_ready_for_pickup', 'manual_payment_reminder', name='notificationtrigger'), nullable=False),
        sa.Column('channel', sa.Enum('whatsapp', 'email', name='notificationchannel'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'sent', 'failed', name='notificationstatus'), nullable=False, server_default='pending'),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('content_snapshot', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['binder_id'], ['binders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_client_id'), 'notifications', ['client_id'], unique=False)
    op.create_index(op.f('ix_notifications_binder_id'), 'notifications', ['binder_id'], unique=False)
    
    # Create permanent_documents table
    op.create_table(
        'permanent_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.Enum('id_copy', 'power_of_attorney', 'engagement_agreement', name='documenttype'), nullable=False),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('is_present', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_permanent_documents_client_id'), 'permanent_documents', ['client_id'], unique=False)


def downgrade() -> None:
    """Drop notifications and permanent_documents tables."""
    
    op.drop_index(op.f('ix_permanent_documents_client_id'), table_name='permanent_documents')
    op.drop_table('permanent_documents')
    
    op.drop_index(op.f('ix_notifications_binder_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_client_id'), table_name='notifications')
    op.drop_table('notifications')
    
    bind = op.get_bind()
    sa.Enum(name='documenttype').drop(bind, checkfirst=True)
    sa.Enum(name='notificationstatus').drop(bind, checkfirst=True)
    sa.Enum(name='notificationchannel').drop(bind, checkfirst=True)
    sa.Enum(name='notificationtrigger').drop(bind, checkfirst=True)