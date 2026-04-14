"""fix annual report line integrity

Revision ID: 0006_fix_annual_report_line_integrity
Revises: 0005_drop_annual_report_detail_credit_cache
Create Date: 2026-04-14

Changes:
- Enforce non-negative income amounts at DB level
- Rename annual report expense external reference field for clarity
- Make annex data owned by annual_report_schedules via schedule_entry_id
- Enforce uniqueness of annual_report_schedules(report, schedule)
"""

from typing import Sequence, Union

import sqlalchemy as sa
import app.utils.enum_utils
from alembic import op


revision: str = "0006_fix_annual_report_line_integrity"
down_revision: Union[str, Sequence[str], None] = "0005_drop_annual_report_detail_credit_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SCHEDULE_ENUM = app.utils.enum_utils._NormalizedEnum(
    "schedule_a",
    "schedule_b",
    "schedule_gimmel",
    "schedule_dalet",
    "form_150",
    "form_1504",
    "form_6111",
    "form_1344",
    "form_1399",
    "form_1350",
    "form_1327",
    "form_1342",
    "form_1343",
    "form_1348",
    "form_858",
    name="annualreportschedule",
)


_DELETE_DUPLICATE_SCHEDULES_SQL = sa.text(
    """
    DELETE FROM annual_report_schedules
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM annual_report_schedules
        GROUP BY annual_report_id, schedule
    )
    """
)

_INSERT_MISSING_SCHEDULES_SQL = sa.text(
    """
    INSERT INTO annual_report_schedules (
        annual_report_id,
        schedule,
        is_required,
        is_complete,
        notes,
        created_at,
        completed_at,
        completed_by
    )
    SELECT DISTINCT
        ad.annual_report_id,
        ad.schedule,
        false,
        false,
        'Auto-created during annex ownership migration',
        CURRENT_TIMESTAMP,
        NULL,
        NULL
    FROM annual_report_annex_data AS ad
    LEFT JOIN annual_report_schedules AS ars
        ON ars.annual_report_id = ad.annual_report_id
       AND ars.schedule = ad.schedule
    WHERE ars.id IS NULL
    """
)

_BACKFILL_SCHEDULE_ENTRY_ID_SQL = sa.text(
    """
    UPDATE annual_report_annex_data
    SET schedule_entry_id = (
        SELECT ars.id
        FROM annual_report_schedules AS ars
        WHERE ars.annual_report_id = annual_report_annex_data.annual_report_id
          AND ars.schedule = annual_report_annex_data.schedule
    )
    """
)

_RENORMALIZE_LINE_NUMBERS_SQL = sa.text(
    """
    WITH ranked AS (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY schedule_entry_id
                ORDER BY line_number, id
            ) AS new_line_number
        FROM annual_report_annex_data
    )
    UPDATE annual_report_annex_data
    SET line_number = (
        SELECT ranked.new_line_number
        FROM ranked
        WHERE ranked.id = annual_report_annex_data.id
    )
    """
)

_DOWNGRADE_BACKFILL_ANNEX_OWNER_SQL = sa.text(
    """
    UPDATE annual_report_annex_data
    SET annual_report_id = (
            SELECT ars.annual_report_id
            FROM annual_report_schedules AS ars
            WHERE ars.id = annual_report_annex_data.schedule_entry_id
        ),
        schedule = (
            SELECT ars.schedule
            FROM annual_report_schedules AS ars
            WHERE ars.id = annual_report_annex_data.schedule_entry_id
        )
    """
)


def upgrade() -> None:
    op.execute(_DELETE_DUPLICATE_SCHEDULES_SQL)

    with op.batch_alter_table("annual_report_income_lines", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_annual_report_income_lines_amount_non_negative",
            "amount >= 0",
        )

    with op.batch_alter_table("annual_report_expense_lines", schema=None) as batch_op:
        batch_op.alter_column(
            "supporting_document_ref",
            new_column_name="external_document_reference",
            existing_type=sa.String(length=255),
            existing_nullable=True,
        )

    with op.batch_alter_table("annual_report_annex_data", schema=None) as batch_op:
        batch_op.add_column(sa.Column("schedule_entry_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_annual_report_annex_data_schedule_entry_id",
            ["schedule_entry_id"],
            unique=False,
        )

    op.execute(_INSERT_MISSING_SCHEDULES_SQL)
    op.execute(_BACKFILL_SCHEDULE_ENTRY_ID_SQL)
    op.execute(_RENORMALIZE_LINE_NUMBERS_SQL)

    with op.batch_alter_table("annual_report_schedules", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_annual_report_schedules_report_schedule",
            ["annual_report_id", "schedule"],
        )

    with op.batch_alter_table("annual_report_annex_data", schema=None) as batch_op:
        batch_op.alter_column("schedule_entry_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_annual_report_annex_data_schedule_entry_id",
            "annual_report_schedules",
            ["schedule_entry_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_annual_report_annex_data_schedule_entry_line",
            ["schedule_entry_id", "line_number"],
        )
        batch_op.drop_column("annual_report_id")
        batch_op.drop_column("schedule")


def downgrade() -> None:
    with op.batch_alter_table("annual_report_annex_data", schema=None) as batch_op:
        batch_op.add_column(sa.Column("annual_report_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("schedule", _SCHEDULE_ENUM, nullable=True))

    op.execute(_DOWNGRADE_BACKFILL_ANNEX_OWNER_SQL)

    with op.batch_alter_table("annual_report_annex_data", schema=None) as batch_op:
        batch_op.alter_column("annual_report_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("schedule", existing_type=sa.String(length=255), nullable=False)
        batch_op.drop_constraint("uq_annual_report_annex_data_schedule_entry_line", type_="unique")
        batch_op.drop_constraint("fk_annual_report_annex_data_schedule_entry_id", type_="foreignkey")
        batch_op.drop_index("ix_annual_report_annex_data_schedule_entry_id")
        batch_op.drop_column("schedule_entry_id")

    with op.batch_alter_table("annual_report_schedules", schema=None) as batch_op:
        batch_op.drop_constraint("uq_annual_report_schedules_report_schedule", type_="unique")

    with op.batch_alter_table("annual_report_expense_lines", schema=None) as batch_op:
        batch_op.alter_column(
            "external_document_reference",
            new_column_name="supporting_document_ref",
            existing_type=sa.String(length=255),
            existing_nullable=True,
        )

    with op.batch_alter_table("annual_report_income_lines", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_annual_report_income_lines_amount_non_negative",
            type_="check",
        )
