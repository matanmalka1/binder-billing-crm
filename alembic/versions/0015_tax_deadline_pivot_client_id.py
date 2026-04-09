"""Pivot tax_deadlines from business_id to client_id.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-04-09

Changes:
- Add client_id column to tax_deadlines (nullable initially)
- Backfill client_id from businesses.client_id via business_id
- Make client_id NOT NULL
- Drop business_id column and its indexes
- Add new index idx_tax_deadline_client_period on (client_id, period)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pass 1 — add client_id nullable
    op.add_column("tax_deadlines", sa.Column("client_id", sa.Integer(), nullable=True))

    # Backfill client_id from businesses
    op.execute(
        """
        UPDATE tax_deadlines
        SET client_id = (
            SELECT client_id FROM businesses
            WHERE businesses.id = tax_deadlines.business_id
        )
        WHERE client_id IS NULL
          AND business_id IS NOT NULL
        """
    )

    # Pass 2 — use batch to make NOT NULL, drop business_id, add FK, swap indexes
    # batch_alter_table recreates the table for SQLite; we explicitly exclude
    # the business_id auto-index (ix_tax_deadlines_business_id) from the copy
    # by not passing copy_from — alembic will use the ORM metadata which has client_id.
    with op.batch_alter_table("tax_deadlines") as batch_op:
        batch_op.alter_column("client_id", nullable=False)
        batch_op.drop_index("ix_tax_deadlines_business_id")
        batch_op.drop_index("idx_tax_deadline_business_period")
        batch_op.drop_column("business_id")
        batch_op.create_foreign_key(
            "fk_tax_deadlines_client_id",
            "clients",
            ["client_id"],
            ["id"],
        )
        batch_op.create_index(
            "idx_tax_deadline_client_period",
            ["client_id", "period"],
        )


def downgrade() -> None:
    with op.batch_alter_table("tax_deadlines") as batch_op:
        batch_op.drop_index("idx_tax_deadline_client_period")
        batch_op.drop_constraint("fk_tax_deadlines_client_id", type_="foreignkey")

    op.add_column("tax_deadlines", sa.Column("business_id", sa.Integer(), nullable=True))
    op.create_index("idx_tax_deadline_business_period", "tax_deadlines", ["business_id", "period"])
    op.drop_column("tax_deadlines", "client_id")
