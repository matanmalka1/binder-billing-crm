"""add_client_record_id_to_signature_requests

Revision ID: 0013_add_client_record_id_to_signature_requests
Revises: 0012_add_client_record_id_to_correspondence
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_add_client_record_id_to_signature_requests"
down_revision: Union[str, None] = "0012_add_client_record_id_to_correspondence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("signature_requests", sa.Column("client_record_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_signature_requests_client_record_id",
        "signature_requests",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index("ix_signature_requests_client_record_id", "signature_requests", ["client_record_id"])


def downgrade() -> None:
    op.drop_index("ix_signature_requests_client_record_id", table_name="signature_requests")
    op.drop_constraint("fk_signature_requests_client_record_id", "signature_requests", type_="foreignkey")
    op.drop_column("signature_requests", "client_record_id")
