"""add annual_report_schedules table

Revision ID: 0018_add_annual_report_schedules_table
Revises: 0017_add_notes_to_advance_payments
Create Date: 2026-03-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0018_add_annual_report_schedules_table"
down_revision: str = "0017_add_notes_to_advance_payments"
branch_labels = None
depends_on = None


schedule_enum = postgresql.ENUM(
    "schedule_b",
    "schedule_bet",
    "schedule_gimmel",
    "schedule_dalet",
    "schedule_heh",
    name="annualreportschedule",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if "annual_report_schedules" not in tables:
        op.create_table(
            "annual_report_schedules",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "annual_report_id",
                sa.Integer(),
                sa.ForeignKey("annual_reports.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("schedule", schedule_enum, nullable=False),
            sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("is_complete", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "idx_annual_report_schedules_report_id",
            "annual_report_schedules",
            ["annual_report_id"],
        )


def downgrade() -> None:
    op.drop_index("idx_annual_report_schedules_report_id", table_name="annual_report_schedules")
    op.drop_table("annual_report_schedules")
