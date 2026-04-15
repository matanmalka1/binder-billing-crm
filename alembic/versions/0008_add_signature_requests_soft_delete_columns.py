"""add signature_requests soft delete columns

Revision ID: 0008_add_signature_requests_soft_delete
Revises: a61d76155e04
Create Date: 2026-04-15

Guard: uses IF NOT EXISTS so this is safe to run on environments where
the columns already exist (e.g. dev/staging) and adds them on prod where
they are missing.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_add_signature_requests_soft_delete"
down_revision: Union[str, Sequence[str], None] = "a61d76155e04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {col["name"] for col in inspector.get_columns("signature_requests")}

    if "deleted_at" not in existing:
        op.add_column("signature_requests", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    if "deleted_by" not in existing:
        op.add_column("signature_requests", sa.Column("deleted_by", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_signature_requests_deleted_by_users",
            "signature_requests",
            "users",
            ["deleted_by"],
            ["id"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {col["name"] for col in inspector.get_columns("signature_requests")}

    if "deleted_by" in existing:
        op.drop_constraint("fk_signature_requests_deleted_by_users", "signature_requests", type_="foreignkey")
        op.drop_column("signature_requests", "deleted_by")

    if "deleted_at" in existing:
        op.drop_column("signature_requests", "deleted_at")
