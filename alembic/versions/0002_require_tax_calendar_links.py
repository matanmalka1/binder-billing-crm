"""Require tax calendar links on obligation rows.

Revision ID: 0002_require_tax_calendar_links
Revises: 9ecbb3d5f408
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_require_tax_calendar_links"
down_revision = "9ecbb3d5f408"
branch_labels = None
depends_on = None

_TABLES = (
    ("vat_work_items", "vat_work_items_tax_calendar_entry_id_fkey"),
    ("advance_payments", "advance_payments_tax_calendar_entry_id_fkey"),
    ("annual_reports", "annual_reports_tax_calendar_entry_id_fkey"),
)


def _assert_no_null_links() -> None:
    conn = op.get_bind()
    for table, _fk in _TABLES:
        count = conn.execute(sa.text(
            f"SELECT COUNT(*) FROM {table} "
            "WHERE deleted_at IS NULL AND tax_calendar_entry_id IS NULL"
        )).scalar()
        if count:
            raise RuntimeError(f"{table} has {count} active rows without tax_calendar_entry_id")


def _set_nullable(nullable: bool) -> None:
    for table, _fk in _TABLES:
        with op.batch_alter_table(table) as batch:
            batch.alter_column("tax_calendar_entry_id", existing_type=sa.Integer(), nullable=nullable)


def _replace_fk(ondelete: str) -> None:
    if op.get_bind().dialect.name == "sqlite":
        return
    for table, fk_name in _TABLES:
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.create_foreign_key(
            fk_name,
            table,
            "tax_calendar_entries",
            ["tax_calendar_entry_id"],
            ["id"],
            ondelete=ondelete,
        )


def upgrade() -> None:
    _assert_no_null_links()
    _replace_fk("RESTRICT")
    _set_nullable(False)


def downgrade() -> None:
    _set_nullable(True)
    _replace_fk("SET NULL")
