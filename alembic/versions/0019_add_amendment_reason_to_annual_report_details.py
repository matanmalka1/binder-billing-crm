"""add amendment_reason to annual_report_details

Revision ID: 0019_add_amendment_reason_to_annual_report_details
Revises: 0018_add_annual_report_schedules_table
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0019_add_amendment_reason_to_annual_report_details"
down_revision = "0018_add_annual_report_schedules_table"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "annual_report_details",
        sa.Column("amendment_reason", sa.String(500), nullable=True),
    )


def downgrade():
    op.drop_column("annual_report_details", "amendment_reason")
