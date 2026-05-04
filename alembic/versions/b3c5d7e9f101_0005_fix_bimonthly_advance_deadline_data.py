"""fix_bimonthly_advance_deadline_data

Revision ID: b3c5d7e9f101
Revises: a2b4c6d8e9f0
Create Date: 2026-05-04 00:00:00.000000

"""
from __future__ import annotations

from datetime import date, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c5d7e9f101"
down_revision: Union[str, Sequence[str], None] = "a2b4c6d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


tax_deadlines = sa.table(
    "tax_deadlines",
    sa.column("id", sa.Integer),
    sa.column("client_record_id", sa.Integer),
    sa.column("deadline_type", sa.String),
    sa.column("period", sa.String),
    sa.column("due_date", sa.Date),
    sa.column("status", sa.String),
    sa.column("completed_at", sa.DateTime),
    sa.column("advance_payment_id", sa.Integer),
    sa.column("payment_amount", sa.Numeric),
    sa.column("description", sa.Text),
    sa.column("deleted_at", sa.DateTime),
)
client_records = sa.table(
    "client_records",
    sa.column("id", sa.Integer),
    sa.column("legal_entity_id", sa.Integer),
)
legal_entities = sa.table(
    "legal_entities",
    sa.column("id", sa.Integer),
    sa.column("vat_reporting_frequency", sa.String),
)


def _due_date_for_bimonthly(period: str) -> date:
    year = int(period[:4])
    start_month = int(period[5:7])
    due_month = start_month + 2
    if due_month > 12:
        return date(year + 1, due_month - 12, 15)
    return date(year, due_month, 15)


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.utcnow()
    rows = conn.execute(
        sa.select(
            tax_deadlines.c.id,
            tax_deadlines.c.period,
            tax_deadlines.c.status,
            tax_deadlines.c.completed_at,
            tax_deadlines.c.advance_payment_id,
            tax_deadlines.c.payment_amount,
        )
        .select_from(
            tax_deadlines
            .join(client_records, tax_deadlines.c.client_record_id == client_records.c.id)
            .join(legal_entities, client_records.c.legal_entity_id == legal_entities.c.id)
        )
        .where(
            legal_entities.c.vat_reporting_frequency == "bimonthly",
            tax_deadlines.c.deleted_at.is_(None),
            tax_deadlines.c.deadline_type == "advance_payment",
            tax_deadlines.c.period.is_not(None),
        )
    ).mappings()

    for row in rows:
        month = int(row["period"][5:7])
        has_activity = any(
            (
                row["status"] != "pending",
                row["completed_at"] is not None,
                row["advance_payment_id"] is not None,
                row["payment_amount"] is not None,
            )
        )
        if month % 2 == 0 and not has_activity:
            conn.execute(
                tax_deadlines.update()
                .where(tax_deadlines.c.id == row["id"])
                .values(deleted_at=now)
            )
            continue
        if month % 2 == 1:
            conn.execute(
                tax_deadlines.update()
                .where(tax_deadlines.c.id == row["id"])
                .values(
                    due_date=_due_date_for_bimonthly(row["period"]),
                    description=f"מקדמה תקופה {month}/{row['period'][:4]}",
                )
            )


def downgrade() -> None:
    pass
