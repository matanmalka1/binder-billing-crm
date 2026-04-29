"""remove other tax deadline type

Revision ID: 0005
Revises: dce588b1e7be
Create Date: 2026-04-28 00:00:00

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0005
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade dce588b1e7be

Notes:
- Removes `other` from the tax deadline type enum.
- Legacy `other` rows are normalized to `national_insurance` before the enum is rebuilt.
- PostgreSQL rebuilds the enum type; SQLite only updates legacy rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "dce588b1e7be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_VALUES = ("vat", "advance_payment", "national_insurance", "annual_report")


def _drop_tax_deadline_enum_dependents() -> None:
    op.drop_index("uq_tax_deadline_active_annual_identity", table_name="tax_deadlines")
    op.drop_index("uq_tax_deadline_active_period_identity", table_name="tax_deadlines")
    op.drop_index("idx_tax_deadline_type", table_name="tax_deadlines")
    op.drop_constraint(
        "ck_tax_deadline_advance_payment_link",
        "tax_deadlines",
        type_="check",
    )


def _create_tax_deadline_enum_dependents() -> None:
    op.create_check_constraint(
        "ck_tax_deadline_advance_payment_link",
        "tax_deadlines",
        "(advance_payment_id IS NULL) OR (deadline_type = 'advance_payment')",
    )
    op.create_index("idx_tax_deadline_type", "tax_deadlines", ["deadline_type"])
    op.create_index(
        "uq_tax_deadline_active_period_identity",
        "tax_deadlines",
        ["client_record_id", "deadline_type", "period"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND period IS NOT NULL"),
    )
    op.create_index(
        "uq_tax_deadline_active_annual_identity",
        "tax_deadlines",
        ["client_record_id", "tax_year"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND deadline_type = 'annual_report' "
            "AND tax_year IS NOT NULL"
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        op.execute(
            "UPDATE tax_deadlines SET deadline_type = 'national_insurance' "
            "WHERE deadline_type = 'other'"
        )
        return

    has_other = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM pg_enum e "
            "JOIN pg_type t ON t.oid = e.enumtypid "
            "WHERE t.typname = 'deadlinetype' AND e.enumlabel = 'other'"
            ")"
        )
    ).scalar()
    if not has_other:
        return

    op.execute(
        "UPDATE tax_deadlines SET deadline_type = 'national_insurance' "
        "WHERE deadline_type = 'other'"
    )
    values = ", ".join(f"'{value}'" for value in NEW_VALUES)
    _drop_tax_deadline_enum_dependents()
    op.execute("ALTER TYPE deadlinetype RENAME TO deadlinetype_old")
    op.execute(f"CREATE TYPE deadlinetype AS ENUM ({values})")
    op.execute(
        "ALTER TABLE tax_deadlines ALTER COLUMN deadline_type "
        "TYPE deadlinetype USING deadline_type::text::deadlinetype"
    )
    op.execute("DROP TYPE deadlinetype_old")
    _create_tax_deadline_enum_dependents()


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE deadlinetype ADD VALUE IF NOT EXISTS 'other'")
