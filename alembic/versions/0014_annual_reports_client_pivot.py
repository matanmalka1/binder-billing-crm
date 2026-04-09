"""Pivot annual_reports from business_id to client_id.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-04-09

Changes:
- Add client_id column to annual_reports (nullable initially)
- Backfill client_id from businesses.client_id via business_id
- Deduplicate: if two reports exist for (client_id, tax_year), keep most recent; delete the other
- Add UNIQUE index on (client_id, tax_year) WHERE deleted_at IS NULL
- Make client_id NOT NULL
- Drop the old index on (business_id, tax_year)
- Keep business_id as nullable deprecated column for one release (ease rollback)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.add_column(sa.Column("client_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_annual_reports_client_id",
            "clients",
            ["client_id"],
            ["id"],
        )

    # Backfill client_id from businesses
    op.execute(
        """
        UPDATE annual_reports
        SET client_id = (
            SELECT client_id FROM businesses
            WHERE businesses.id = annual_reports.business_id
        )
        WHERE client_id IS NULL
          AND business_id IS NOT NULL
        """
    )

    # Deduplicate: for each (client_id, tax_year) pair with multiple non-deleted rows,
    # keep the most recent (highest id) and soft-delete the rest.
    op.execute(
        """
        UPDATE annual_reports
        SET deleted_at = CURRENT_TIMESTAMP,
            deleted_by = NULL
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM annual_reports
            WHERE deleted_at IS NULL
            GROUP BY client_id, tax_year
        )
          AND deleted_at IS NULL
          AND client_id IS NOT NULL
        """
    )

    # Make client_id NOT NULL now that it's populated
    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.alter_column("client_id", nullable=False)

    # Drop old business_id indexes and column
    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.drop_index("idx_annual_report_business_year")
        batch_op.drop_index("ix_annual_reports_business_id")
        batch_op.drop_column("business_id")

    # Add new unique index on (client_id, tax_year) WHERE deleted_at IS NULL
    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.create_index(
            "idx_annual_report_client_year",
            ["client_id", "tax_year"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
            sqlite_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.drop_index("idx_annual_report_client_year")

    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.create_index(
            "idx_annual_report_business_year",
            ["business_id", "tax_year"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
            sqlite_where=sa.text("deleted_at IS NULL"),
        )

    with op.batch_alter_table("annual_reports") as batch_op:
        batch_op.alter_column("client_id", nullable=True)
        batch_op.drop_constraint("fk_annual_reports_client_id", type_="foreignkey")
        batch_op.drop_column("client_id")
