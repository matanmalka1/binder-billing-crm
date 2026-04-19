"""add_client_record_id_to_authority_contacts

Revision ID: 0014_add_client_record_id_to_authority_contacts
Revises: 0013_add_client_record_id_to_signature_requests
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_add_client_record_id_to_authority_contacts"
down_revision: Union[str, None] = "0013_add_client_record_id_to_signature_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("authority_contacts", sa.Column("client_record_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_authority_contacts_client_record_id",
        "authority_contacts",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index("ix_authority_contacts_client_record_id", "authority_contacts", ["client_record_id"])


def downgrade() -> None:
    op.drop_index("ix_authority_contacts_client_record_id", table_name="authority_contacts")
    op.drop_constraint("fk_authority_contacts_client_record_id", "authority_contacts", type_="foreignkey")
    op.drop_column("authority_contacts", "client_record_id")
