"""binder_number_unique_per_client

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-26 12:20:00.000000

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0004
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0003

Notes:
- Replaces in-office-only binder number uniqueness with per-client uniqueness.
- Existing duplicate non-deleted binders per client must be resolved before upgrade.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes("binders")}
    if "idx_active_binder_unique" in existing:
        op.drop_index(
            "idx_active_binder_unique",
            table_name="binders",
            postgresql_where=sa.text("status = 'in_office' AND deleted_at IS NULL"),
        )
    if "uq_binder_number_per_client" not in existing:
        op.create_index(
            "uq_binder_number_per_client",
            "binders",
            ["client_record_id", "binder_number"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    existing = {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes("binders")}
    if "uq_binder_number_per_client" in existing:
        op.drop_index(
            "uq_binder_number_per_client",
            table_name="binders",
            postgresql_where=sa.text("deleted_at IS NULL"),
        )
    if "idx_active_binder_unique" not in existing:
        op.create_index(
            "idx_active_binder_unique",
            "binders",
            ["binder_number"],
            unique=True,
            postgresql_where=sa.text("status = 'in_office' AND deleted_at IS NULL"),
        )
