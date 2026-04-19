"""make_client_record_id_not_null

Revision ID: 0018_make_client_record_id_not_null
Revises: 0017_backfill_client_record_id_to_permanent_documents
Create Date: 2026-04-19

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0018_make_client_record_id_not_null
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0017_backfill_client_record_id_to_permanent_documents

Notes:
- Makes client_record_id NOT NULL on all 13 workflow tables.
- Pre-flight: counts NULLs in each table before altering. Raises if any are found.
- Tables covered: annual_reports, vat_work_items, tax_deadlines, binders,
  advance_payments, reminders, charges, notifications, correspondence_entries,
  signature_requests, authority_contacts, binder_handovers, permanent_documents.
- PostgreSQL: uses ALTER COLUMN SET NOT NULL directly.
- SQLite: uses batch_alter_table (recreate='auto').
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_make_client_record_id_not_null"
down_revision: Union[str, None] = "0017_backfill_client_record_id_to_permanent_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "annual_reports",
    "vat_work_items",
    "tax_deadlines",
    "binders",
    "advance_payments",
    "reminders",
    "charges",
    "notifications",
    "correspondence_entries",
    "signature_requests",
    "authority_contacts",
    "binder_handovers",
    "permanent_documents",
]


def _count_nulls(bind, table: str) -> int:
    result = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {table} WHERE client_record_id IS NULL")
    )
    return result.scalar() or 0


def upgrade() -> None:
    bind = op.get_bind()

    # Pre-flight: abort if any table has NULLs.
    null_counts = {t: _count_nulls(bind, t) for t in _TABLES}
    failing = {t: n for t, n in null_counts.items() if n > 0}
    if failing:
        raise RuntimeError(
            f"Cannot make client_record_id NOT NULL — found NULL rows: {failing}"
        )

    dialect = bind.dialect.name
    for table in _TABLES:
        if dialect == "sqlite":
            with op.batch_alter_table(table, recreate="auto") as batch_op:
                batch_op.alter_column(
                    "client_record_id",
                    existing_type=sa.Integer(),
                    nullable=False,
                )
        else:
            op.alter_column(
                table,
                "client_record_id",
                existing_type=sa.Integer(),
                nullable=False,
            )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    for table in reversed(_TABLES):
        if dialect == "sqlite":
            with op.batch_alter_table(table, recreate="auto") as batch_op:
                batch_op.alter_column(
                    "client_record_id",
                    existing_type=sa.Integer(),
                    nullable=True,
                )
        else:
            op.alter_column(
                table,
                "client_record_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
