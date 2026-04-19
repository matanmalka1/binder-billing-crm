"""add_client_record_id_to_permanent_documents

Revision ID: 0016_add_client_record_id_to_permanent_documents
Revises: 0015_add_client_record_id_to_binder_handovers
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_add_client_record_id_to_permanent_documents"
down_revision: Union[str, None] = "0015_add_client_record_id_to_binder_handovers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("permanent_documents", sa.Column("client_record_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_permanent_documents_client_record_id",
        "permanent_documents",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index(
        "ix_permanent_documents_client_record_id",
        "permanent_documents",
        ["client_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_permanent_documents_client_record_id", table_name="permanent_documents")
    op.drop_constraint("fk_permanent_documents_client_record_id", "permanent_documents", type_="foreignkey")
    op.drop_column("permanent_documents", "client_record_id")
