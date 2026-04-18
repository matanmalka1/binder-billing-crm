"""add office_client_number to clients

Revision ID: 0009_add_office_client_number
Revises: 0008_add_signature_requests_soft_delete
Create Date: 2026-04-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_add_office_client_number"
down_revision: Union[str, Sequence[str], None] = "0008_add_signature_requests_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("clients") as batch_op:
        batch_op.add_column(sa.Column("office_client_number", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_clients_office_client_number_active",
            ["office_client_number"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
            sqlite_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    with op.batch_alter_table("clients") as batch_op:
        batch_op.drop_index("ix_clients_office_client_number_active")
        batch_op.drop_column("office_client_number")
