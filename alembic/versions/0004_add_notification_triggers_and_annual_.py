"""add_notification_triggers_and_annual_report_id

Revision ID: dce588b1e7be
Revises: 966f3c2d3267
Create Date: 2026-04-28 14:02:05.804172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dce588b1e7be'
down_revision: Union[str, Sequence[str], None] = '966f3c2d3267'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE notificationtrigger ADD VALUE IF NOT EXISTS 'pickup_reminder'")
    op.execute("ALTER TYPE notificationtrigger ADD VALUE IF NOT EXISTS 'annual_report_client_reminder'")
    op.add_column('notifications', sa.Column('annual_report_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_notifications_annual_report_id'), 'notifications', ['annual_report_id'], unique=False)
    op.create_foreign_key(None, 'notifications', 'annual_reports', ['annual_report_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'notifications', type_='foreignkey')
    op.drop_index(op.f('ix_notifications_annual_report_id'), table_name='notifications')
    op.drop_column('notifications', 'annual_report_id')
