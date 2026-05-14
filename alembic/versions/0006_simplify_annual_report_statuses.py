"""simplify annual report statuses

Revision ID: 0006_simplify_annual_report_statuses
Revises: 0005_task_assigned_role_pg_enum
Create Date: 2026-05-14 00:00:00.000000

Run:
- Upgrade:   APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic upgrade 0006_simplify_annual_report_statuses
- Downgrade: APP_ENV=<env> ENV_FILE=<env_file> python3 -m alembic downgrade 0005_task_assigned_role_pg_enum

Notes:
- Collapses detailed annual-report lifecycle statuses into the operational set:
  not_started, collecting_docs, in_preparation, pending_client, submitted, closed, canceled.
- Existing values are remapped before shrinking the PostgreSQL enum.
- Downgrade restores the wider enum labels but cannot reconstruct the exact collapsed history.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_simplify_annual_report_statuses"
down_revision: Union[str, Sequence[str], None] = "0005_task_assigned_role_pg_enum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_VALUES = (
    "not_started",
    "collecting_docs",
    "docs_complete",
    "in_preparation",
    "pending_client",
    "submitted",
    "amended",
    "accepted",
    "assessment_issued",
    "objection_filed",
    "closed",
    "canceled",
)
NEW_VALUES = (
    "not_started",
    "collecting_docs",
    "in_preparation",
    "pending_client",
    "submitted",
    "closed",
    "canceled",
)


def _remap_status_values() -> None:
    for table, columns in {
        "annual_reports": ("status",),
        "annual_report_status_history": ("from_status", "to_status"),
    }.items():
        for column in columns:
            op.execute(
                sa.text(
                    f"""
                    UPDATE {table}
                    SET {column} = CASE
                        WHEN {column} = 'docs_complete' THEN 'in_preparation'
                        WHEN {column} = 'amended' THEN 'in_preparation'
                        WHEN {column} = 'accepted' THEN 'closed'
                        WHEN {column} = 'assessment_issued' THEN 'closed'
                        WHEN {column} = 'objection_filed' THEN 'closed'
                        ELSE {column}
                    END
                    WHERE {column} IN (
                        'docs_complete',
                        'amended',
                        'accepted',
                        'assessment_issued',
                        'objection_filed'
                    )
                    """
                )
            )


def upgrade() -> None:
    bind = op.get_bind()
    _remap_status_values()

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text("ALTER TYPE annualreportstatus RENAME TO annualreportstatus_old")
        )
        new_enum = postgresql.ENUM(*NEW_VALUES, name="annualreportstatus")
        new_enum.create(bind, checkfirst=False)
        for table, column, nullable in (
            ("annual_reports", "status", False),
            ("annual_report_status_history", "from_status", True),
            ("annual_report_status_history", "to_status", False),
        ):
            op.alter_column(
                table,
                column,
                type_=new_enum,
                existing_type=postgresql.ENUM(
                    *OLD_VALUES, name="annualreportstatus_old"
                ),
                existing_nullable=nullable,
                postgresql_using=f"{column}::text::annualreportstatus",
            )
        op.execute(sa.text("DROP TYPE annualreportstatus_old"))
        return

    for table, column, nullable in (
        ("annual_reports", "status", False),
        ("annual_report_status_history", "from_status", True),
        ("annual_report_status_history", "to_status", False),
    ):
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*OLD_VALUES, name="annualreportstatus"),
                type_=sa.Enum(*NEW_VALUES, name="annualreportstatus"),
                existing_nullable=nullable,
            )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TYPE annualreportstatus RENAME TO annualreportstatus_new"))
        old_enum = postgresql.ENUM(*OLD_VALUES, name="annualreportstatus")
        old_enum.create(bind, checkfirst=False)
        for table, column, nullable in (
            ("annual_reports", "status", False),
            ("annual_report_status_history", "from_status", True),
            ("annual_report_status_history", "to_status", False),
        ):
            op.alter_column(
                table,
                column,
                type_=old_enum,
                existing_type=postgresql.ENUM(
                    *NEW_VALUES, name="annualreportstatus_new"
                ),
                existing_nullable=nullable,
                postgresql_using=f"{column}::text::annualreportstatus",
            )
        op.execute(sa.text("DROP TYPE annualreportstatus_new"))
        return

    for table, column, nullable in (
        ("annual_reports", "status", False),
        ("annual_report_status_history", "from_status", True),
        ("annual_report_status_history", "to_status", False),
    ):
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*NEW_VALUES, name="annualreportstatus"),
                type_=sa.Enum(*OLD_VALUES, name="annualreportstatus"),
                existing_nullable=nullable,
            )
