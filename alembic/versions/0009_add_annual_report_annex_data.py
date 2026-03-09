"""add annual_report_annex_data table

Revision ID: 0009_add_annual_report_annex_data
Revises: 0008_add_annual_report_id_to_advance_payments
Create Date: 2026-03-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '0009_add_annual_report_annex_data'
down_revision: Union[str, Sequence[str], None] = '0008_add_annual_report_id_to_advance_payments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    # Create the enum type only if it doesn't already exist (idempotent for PostgreSQL)
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE annualreportschedule AS ENUM ("
            "'schedule_b', 'schedule_bet', 'schedule_gimmel', 'schedule_dalet', 'schedule_heh'"
            "); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        ))

    if "annual_report_annex_data" not in tables:
        op.create_table(
            "annual_report_annex_data",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("annual_report_id", sa.Integer(), sa.ForeignKey("annual_reports.id"), nullable=False),
            sa.Column(
                "schedule",
                sa.Enum(
                    "schedule_b", "schedule_bet", "schedule_gimmel",
                    "schedule_dalet", "schedule_heh",
                    name="annualreportschedule",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("line_number", sa.Integer(), nullable=False),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "idx_annex_data_report_id",
            "annual_report_annex_data",
            ["annual_report_id"],
        )


def downgrade() -> None:
    op.drop_index("idx_annex_data_report_id", table_name="annual_report_annex_data")
    op.drop_table("annual_report_annex_data")
