"""fix_bimonthly_advance_payment_data

Revision ID: a2b4c6d8e9f0
Revises: f1a2b3c4d5e6
Create Date: 2026-05-04 00:00:00.000000

"""
from __future__ import annotations

from datetime import date, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b4c6d8e9f0"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


advance_payments = sa.table(
    "advance_payments",
    sa.column("id", sa.Integer),
    sa.column("client_record_id", sa.Integer),
    sa.column("period", sa.String),
    sa.column("period_months_count", sa.Integer),
    sa.column("due_date", sa.Date),
    sa.column("paid_amount", sa.Numeric),
    sa.column("status", sa.String),
    sa.column("paid_at", sa.DateTime),
    sa.column("annual_report_id", sa.Integer),
    sa.column("reported_turnover", sa.Numeric),
    sa.column("turnover_source_vat_work_item_id", sa.Integer),
    sa.column("updated_at", sa.DateTime),
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
            advance_payments.c.id,
            advance_payments.c.period,
            advance_payments.c.paid_amount,
            advance_payments.c.status,
            advance_payments.c.paid_at,
            advance_payments.c.annual_report_id,
            advance_payments.c.reported_turnover,
            advance_payments.c.turnover_source_vat_work_item_id,
        )
        .select_from(
            advance_payments
            .join(client_records, advance_payments.c.client_record_id == client_records.c.id)
            .join(legal_entities, client_records.c.legal_entity_id == legal_entities.c.id)
        )
        .where(
            legal_entities.c.vat_reporting_frequency == "bimonthly",
            advance_payments.c.deleted_at.is_(None),
            advance_payments.c.period_months_count == 1,
        )
    ).mappings()

    for row in rows:
        month = int(row["period"][5:7])
        has_activity = any(
            (
                row["status"] != "pending",
                row["paid_amount"] not in (None, 0),
                row["paid_at"] is not None,
                row["annual_report_id"] is not None,
                row["reported_turnover"] is not None,
                row["turnover_source_vat_work_item_id"] is not None,
            )
        )
        if month % 2 == 0 and not has_activity:
            conn.execute(
                advance_payments.update()
                .where(advance_payments.c.id == row["id"])
                .values(deleted_at=now, updated_at=now)
            )
            continue
        if month % 2 == 1:
            conn.execute(
                advance_payments.update()
                .where(advance_payments.c.id == row["id"])
                .values(
                    period_months_count=2,
                    due_date=_due_date_for_bimonthly(row["period"]),
                    updated_at=now,
                )
            )


def downgrade() -> None:
    # Data correction is intentionally not reversible without risking valid rows.
    pass
