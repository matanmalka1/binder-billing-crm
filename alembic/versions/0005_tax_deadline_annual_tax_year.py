"""tax_deadline_annual_tax_year

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-26 12:40:00.000000

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0005
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0004

Notes:
- Adds tax_year to tax_deadlines for annual_report deadline identity.
- Adds DB-level uniqueness for active annual report deadlines per client/year.
- Existing duplicate active annual rows for the same client/year must be resolved before upgrade.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tax_deadlines", sa.Column("tax_year", sa.Integer(), nullable=True))
    tax_deadlines = sa.table(
        "tax_deadlines",
        sa.column("deadline_type", sa.String()),
        sa.column("due_date", sa.Date()),
        sa.column("tax_year", sa.Integer()),
    )
    op.execute(
        tax_deadlines.update()
        .where(tax_deadlines.c.deadline_type == "annual_report")
        .where(tax_deadlines.c.tax_year.is_(None))
        .values(tax_year=sa.cast(sa.extract("year", tax_deadlines.c.due_date), sa.Integer) - 1)
    )
    op.create_index(
        "uq_tax_deadline_active_annual_identity",
        "tax_deadlines",
        ["client_record_id", "tax_year"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND deadline_type = 'annual_report' AND tax_year IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_tax_deadline_active_annual_identity",
        table_name="tax_deadlines",
        postgresql_where=sa.text(
            "deleted_at IS NULL AND deadline_type = 'annual_report' AND tax_year IS NOT NULL"
        ),
    )
    op.drop_column("tax_deadlines", "tax_year")
