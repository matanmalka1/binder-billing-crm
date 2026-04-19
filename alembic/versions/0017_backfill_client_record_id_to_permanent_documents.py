"""backfill_client_record_id_to_permanent_documents

Revision ID: 0017_backfill_client_record_id_to_permanent_documents
Revises: 0016_add_client_record_id_to_permanent_documents
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017_backfill_client_record_id_to_permanent_documents"
down_revision: Union[str, None] = "0016_add_client_record_id_to_permanent_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    result = op.get_bind().execute(
        sa.text(
            """
            UPDATE permanent_documents
            SET client_record_id = client_id
            WHERE client_record_id IS NULL
            """
        )
    )
    print(f"Permanent documents backfill count: {result.rowcount or 0}")


def downgrade() -> None:
    pass
