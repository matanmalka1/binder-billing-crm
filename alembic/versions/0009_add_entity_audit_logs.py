"""add entity_audit_logs table

Revision ID: a1b2c3d4e5f6
Revises: 71ead2aae8c6
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '71ead2aae8c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'entity_audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('performed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('performed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_entity_audit_type_id', 'entity_audit_logs', ['entity_type', 'entity_id'])
    op.create_index(op.f('ix_entity_audit_logs_entity_id'), 'entity_audit_logs', ['entity_id'])
    op.create_index(op.f('ix_entity_audit_logs_entity_type'), 'entity_audit_logs', ['entity_type'])


def downgrade() -> None:
    op.drop_index(op.f('ix_entity_audit_logs_entity_type'), table_name='entity_audit_logs')
    op.drop_index(op.f('ix_entity_audit_logs_entity_id'), table_name='entity_audit_logs')
    op.drop_index('idx_entity_audit_type_id', table_name='entity_audit_logs')
    op.drop_table('entity_audit_logs')
