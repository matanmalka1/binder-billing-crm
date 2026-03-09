"""add severity and is_read to notifications

Revision ID: 0020_add_severity_is_read_to_notifications
Revises: 0019_add_amendment_reason_to_annual_report_details
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0020_add_severity_is_read_to_notifications"
down_revision = "0019_add_amendment_reason_to_annual_report_details"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notifications",
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
    )
    op.add_column(
        "notifications",
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "notifications",
        sa.Column("read_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("notifications", "read_at")
    op.drop_column("notifications", "is_read")
    op.drop_column("notifications", "severity")
