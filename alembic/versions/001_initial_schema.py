"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('advisor', 'secretary', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # clients
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('id_number', sa.String(), nullable=False),
        sa.Column('client_type', sa.Enum('osek_patur', 'osek_murshe', 'company', 'employee', name='clienttype'), nullable=False),
        sa.Column('status', sa.Enum('active', 'frozen', 'closed', name='clientstatus'), nullable=False),
        sa.Column('primary_binder_number', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('opened_at', sa.Date(), nullable=False),
        sa.Column('closed_at', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_id_number'), 'clients', ['id_number'], unique=True)

    # binders
    op.create_table(
        'binders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('binder_number', sa.String(), nullable=False),
        sa.Column('received_at', sa.Date(), nullable=False),
        sa.Column('expected_return_at', sa.Date(), nullable=False),
        sa.Column('returned_at', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('in_office', 'ready_for_pickup', 'returned', 'overdue', name='binderstatus'), nullable=False),
        sa.Column('received_by', sa.Integer(), nullable=False),
        sa.Column('returned_by', sa.Integer(), nullable=True),
        sa.Column('pickup_person_name', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['received_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['returned_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_binders_client_id'), 'binders', ['client_id'], unique=False)
    op.create_index('idx_binder_status', 'binders', ['status'], unique=False)
    op.create_index('idx_binder_received_at', 'binders', ['received_at'], unique=False)
    op.create_index('idx_binder_expected_return_at', 'binders', ['expected_return_at'], unique=False)

    # binder_status_logs
    op.create_table(
        'binder_status_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('binder_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.String(), nullable=False),
        sa.Column('new_status', sa.String(), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['binder_id'], ['binders.id'], ),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_binder_status_logs_binder_id'), 'binder_status_logs', ['binder_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_binder_status_logs_binder_id'), table_name='binder_status_logs')
    op.drop_table('binder_status_logs')
    op.drop_index('idx_binder_expected_return_at', table_name='binders')
    op.drop_index('idx_binder_received_at', table_name='binders')
    op.drop_index('idx_binder_status', table_name='binders')
    op.drop_index(op.f('ix_binders_client_id'), table_name='binders')
    op.drop_table('binders')
    op.drop_index(op.f('ix_clients_id_number'), table_name='clients')
    op.drop_table('clients')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')