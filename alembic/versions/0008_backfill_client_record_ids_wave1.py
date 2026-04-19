"""backfill_client_record_ids_wave1

Revision ID: 0008_backfill_client_record_ids_wave1
Revises: 0007_add_client_record_id_to_advance_payments
Create Date: 2026-04-19

Backfills Wave 1 client_record_id columns from legacy client_id values.
Also backfills businesses.legal_entity_id from the same legacy mapping.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_backfill_client_record_ids_wave1"
down_revision: Union[str, None] = "0007_add_client_record_id_to_advance_payments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill(bind, table_name: str, target_column: str, source_column: str) -> int:
    result = bind.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET {target_column} = {source_column}
            WHERE {target_column} IS NULL
            """
        )
    )
    return result.rowcount or 0


def upgrade() -> None:
    bind = op.get_bind()
    counts = {
        "annual_reports": _backfill(bind, "annual_reports", "client_record_id", "client_id"),
        "vat_work_items": _backfill(bind, "vat_work_items", "client_record_id", "client_id"),
        "tax_deadlines": _backfill(bind, "tax_deadlines", "client_record_id", "client_id"),
        "binders": _backfill(bind, "binders", "client_record_id", "client_id"),
        "advance_payments": _backfill(bind, "advance_payments", "client_record_id", "client_id"),
        "businesses": _backfill(bind, "businesses", "legal_entity_id", "client_id"),
    }
    print(f"Wave 1 backfill counts: {counts}")


def downgrade() -> None:
    pass
