"""binder domain alignment

Revision ID: 0010_binder_domain_alignment
Revises: 0009_add_office_client_number
Create Date: 2026-04-16

Steps:
  A. Add closed_in_office to binderstatus PostgreSQL enum (SQLite: string column, no-op)
  B. Add structured period fields + vat_report_id to binder_intake_materials
  C. Create binder_handovers, binder_handover_binders, binder_intake_edit_logs tables
  D. Data migration: is_full=True rows -> status=closed_in_office
  E. Drop is_full column from binders
  F. Backfill period_year/month from description where parseable; leave NULL otherwise
  G. Make binders.period_start nullable
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_binder_domain_alignment"
down_revision: Union[str, Sequence[str], None] = "0009_add_office_client_number"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step A: Add closed_in_office to enum (PostgreSQL only) ────────────────
    if _is_postgres():
        conn.execute(sa.text(
            "ALTER TYPE binderstatus ADD VALUE IF NOT EXISTS 'closed_in_office' "
            "BEFORE 'ready_for_pickup'"
        ))

    # ── Step B: binder_intake_materials — structured period + vat_report_id ──
    with op.batch_alter_table("binder_intake_materials") as batch_op:
        batch_op.add_column(sa.Column("period_year", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("period_month_start", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("period_month_end", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("vat_report_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_binder_intake_material_vat_report",
            "vat_work_items",
            ["vat_report_id"], ["id"],
        )
        batch_op.create_index("idx_intake_material_vat_report", ["vat_report_id"])

    # ── Step C: New tables ────────────────────────────────────────────────────
    op.create_table(
        "binder_handovers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("received_by_name", sa.String(), nullable=False),
        sa.Column("handed_over_at", sa.Date(), nullable=False),
        sa.Column("until_period_year", sa.Integer(), nullable=False),
        sa.Column("until_period_month", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_binder_handover_client", "binder_handovers", ["client_id"])

    op.create_table(
        "binder_handover_binders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("handover_id", sa.Integer(), sa.ForeignKey("binder_handovers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("binder_id", sa.Integer(), sa.ForeignKey("binders.id"), nullable=False),
    )
    op.create_index("idx_handover_binder_handover", "binder_handover_binders", ["handover_id"])
    op.create_index("idx_handover_binder_binder", "binder_handover_binders", ["binder_id"])
    op.create_index("idx_handover_binder_unique", "binder_handover_binders", ["handover_id", "binder_id"], unique=True)

    op.create_table(
        "binder_intake_edit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("intake_id", sa.Integer(), sa.ForeignKey("binder_intakes.id"), nullable=False),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_intake_edit_log_intake", "binder_intake_edit_logs", ["intake_id"])

    # ── Step D: Migrate is_full=True rows → closed_in_office ─────────────────
    conn.execute(sa.text(
        "UPDATE binders SET status = 'closed_in_office' WHERE is_full = 1 AND status != 'returned'"
    ))

    # ── Step E: Drop is_full column ───────────────────────────────────────────
    # Also drop the old idx_active_binder_unique (it must be recreated with new semantics).
    with op.batch_alter_table("binders") as batch_op:
        batch_op.drop_index("idx_active_binder_unique")
        batch_op.drop_column("is_full")
        # Recreate index: unique binder_number for IN_OFFICE (open) non-deleted binders only.
        batch_op.create_index(
            "idx_active_binder_unique",
            ["binder_number"],
            unique=True,
            postgresql_where=sa.text("status = 'in_office' AND deleted_at IS NULL"),
            sqlite_where=sa.text("status = 'in_office' AND deleted_at IS NULL"),
        )
        # Make period_start nullable (Step G bundled here to use one batch_alter_table call).
        batch_op.alter_column("period_start", existing_type=sa.Date(), nullable=True)

    # ── Step F: Backfill structured period from description where parseable ───
    # Uses the same parse logic as parse_period_to_date in binder_helpers.py.
    # Rows that cannot be parsed are left with NULL period fields.
    # Format "YYYY-MM" -> year=YYYY, month_start=MM, month_end=MM
    # Format "YYYY-MM-MM2" -> year=YYYY, month_start=MM, month_end=MM2
    # Format "YYYY" -> year=YYYY, month_start=1, month_end=12
    materials = conn.execute(sa.text(
        "SELECT id, description FROM binder_intake_materials "
        "WHERE description IS NOT NULL AND period_year IS NULL"
    )).fetchall()

    for row in materials:
        mat_id, desc = row
        if not desc:
            continue
        parts = desc.strip().split("-")
        try:
            if len(parts) == 1:
                year = int(parts[0])
                conn.execute(sa.text(
                    "UPDATE binder_intake_materials "
                    "SET period_year=:y, period_month_start=1, period_month_end=12 WHERE id=:id"
                ), {"y": year, "id": mat_id})
            elif len(parts) == 2:
                year, month = int(parts[0]), int(parts[1])
                if 1 <= month <= 12:
                    conn.execute(sa.text(
                        "UPDATE binder_intake_materials "
                        "SET period_year=:y, period_month_start=:ms, period_month_end=:me WHERE id=:id"
                    ), {"y": year, "ms": month, "me": month, "id": mat_id})
            elif len(parts) == 3:
                year, month_start, month_end = int(parts[0]), int(parts[1]), int(parts[2])
                if 1 <= month_start <= 12 and 1 <= month_end <= 12:
                    conn.execute(sa.text(
                        "UPDATE binder_intake_materials "
                        "SET period_year=:y, period_month_start=:ms, period_month_end=:me WHERE id=:id"
                    ), {"y": year, "ms": month_start, "me": month_end, "id": mat_id})
        except (ValueError, TypeError):
            # Leave period fields NULL — cannot be parsed. Manual review required.
            pass


def downgrade() -> None:
    # Restore is_full column (values lost — all set to False).
    with op.batch_alter_table("binders") as batch_op:
        batch_op.drop_index("idx_active_binder_unique")
        batch_op.add_column(sa.Column("is_full", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.alter_column("period_start", existing_type=sa.Date(), nullable=False)
        batch_op.create_index(
            "idx_active_binder_unique",
            ["binder_number"],
            unique=True,
            postgresql_where=sa.text("status != 'returned' AND deleted_at IS NULL"),
            sqlite_where=sa.text("status != 'returned' AND deleted_at IS NULL"),
        )

    with op.batch_alter_table("binder_intake_materials") as batch_op:
        batch_op.drop_index("idx_intake_material_vat_report")
        batch_op.drop_constraint("fk_binder_intake_material_vat_report", type_="foreignkey")
        batch_op.drop_column("vat_report_id")
        batch_op.drop_column("period_month_end")
        batch_op.drop_column("period_month_start")
        batch_op.drop_column("period_year")

    op.drop_index("idx_intake_edit_log_intake", "binder_intake_edit_logs")
    op.drop_table("binder_intake_edit_logs")
    op.drop_index("idx_handover_binder_unique", "binder_handover_binders")
    op.drop_index("idx_handover_binder_binder", "binder_handover_binders")
    op.drop_index("idx_handover_binder_handover", "binder_handover_binders")
    op.drop_table("binder_handover_binders")
    op.drop_index("idx_binder_handover_client", "binder_handovers")
    op.drop_table("binder_handovers")

    # NOTE: PostgreSQL enum value removal requires manual ALTER TYPE and is not performed here.
