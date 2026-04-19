"""add_client_record_id_to_binder_handovers

Revision ID: 0015_add_client_record_id_to_binder_handovers
Revises: 0014_add_client_record_id_to_authority_contacts
Create Date: 2026-04-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015_add_client_record_id_to_binder_handovers"
down_revision: Union[str, None] = "0014_add_client_record_id_to_authority_contacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("binder_handovers", sa.Column("client_record_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_binder_handovers_client_record_id",
        "binder_handovers",
        "client_records",
        ["client_record_id"],
        ["id"],
    )
    op.create_index("ix_binder_handovers_client_record_id", "binder_handovers", ["client_record_id"])


def downgrade() -> None:
    op.drop_index("ix_binder_handovers_client_record_id", table_name="binder_handovers")
    op.drop_constraint("fk_binder_handovers_client_record_id", "binder_handovers", type_="foreignkey")
    op.drop_column("binder_handovers", "client_record_id")
