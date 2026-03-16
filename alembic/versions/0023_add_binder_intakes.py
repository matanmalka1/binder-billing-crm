"""add binder intakes

Revision ID: 0023_add_binder_intakes
Revises: 0022_drop_legacy_address_from_clients
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from datetime import datetime

revision = "0023_add_binder_intakes"
down_revision = "0022_drop_legacy_address_from_clients"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "binder_intakes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("binder_id", sa.Integer(), sa.ForeignKey("binders.id"), nullable=False),
        sa.Column("received_at", sa.Date(), nullable=False),
        sa.Column("received_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_binder_intake_binder_id", "binder_intakes", ["binder_id"])

    # Backfill: create one intake per existing non-deleted binder
    binders_table = table(
        "binders",
        column("id", sa.Integer),
        column("received_at", sa.Date),
        column("received_by", sa.Integer),
        column("notes", sa.Text),
        column("deleted_at", sa.DateTime),
    )
    intakes_table = table(
        "binder_intakes",
        column("binder_id", sa.Integer),
        column("received_at", sa.Date),
        column("received_by", sa.Integer),
        column("notes", sa.Text),
        column("created_at", sa.DateTime),
    )

    conn = op.get_bind()
    binders = conn.execute(
        sa.select(
            binders_table.c.id,
            binders_table.c.received_at,
            binders_table.c.received_by,
            binders_table.c.notes,
        ).where(binders_table.c.deleted_at.is_(None))
    ).fetchall()

    now = datetime.utcnow()
    if binders:
        conn.execute(
            intakes_table.insert(),
            [
                {
                    "binder_id": b.id,
                    "received_at": b.received_at,
                    "received_by": b.received_by,
                    "notes": b.notes,
                    "created_at": now,
                }
                for b in binders
            ],
        )


def downgrade() -> None:
    op.drop_index("idx_binder_intake_binder_id", table_name="binder_intakes")
    op.drop_table("binder_intakes")
