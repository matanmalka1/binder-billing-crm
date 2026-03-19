"""add restored_at and restored_by to clients

Revision ID: d1e2f3a4b5c6
Revises: c3f9b0a1d2e4
Create Date: 2026-03-19 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c3f9b0a1d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("restored_at", sa.DateTime(), nullable=True))
    op.add_column(
        "clients",
        sa.Column("restored_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clients", "restored_by")
    op.drop_column("clients", "restored_at")
