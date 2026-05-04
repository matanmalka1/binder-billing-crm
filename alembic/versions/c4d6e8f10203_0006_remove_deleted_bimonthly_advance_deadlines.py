"""remove_deleted_bimonthly_advance_deadlines

Revision ID: c4d6e8f10203
Revises: b3c5d7e9f101
Create Date: 2026-05-04 00:00:00.000000

"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d6e8f10203"
down_revision: Union[str, Sequence[str], None] = "b3c5d7e9f101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.utcnow()
    op.execute(
        sa.text(
            """
            UPDATE tax_deadlines td
            SET deleted_at = :now
            FROM client_records cr
            JOIN legal_entities le ON cr.legal_entity_id = le.id
            WHERE td.client_record_id = cr.id
              AND le.vat_reporting_frequency = 'bimonthly'
              AND td.deadline_type = 'advance_payment'
              AND td.deleted_at IS NULL
              AND td.period IS NOT NULL
              AND (substring(td.period from 6 for 2)::int % 2) = 0
              AND td.status = 'pending'
              AND td.completed_at IS NULL
              AND td.payment_amount IS NULL
              AND (
                td.advance_payment_id IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM advance_payments ap
                    WHERE ap.id = td.advance_payment_id
                      AND ap.deleted_at IS NOT NULL
                )
              )
            """
        ).bindparams(now=now)
    )


def downgrade() -> None:
    pass
