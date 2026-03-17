"""extend vat invoices and work items for Israeli VAT law compliance

Revision ID: 0024_extend_vat_invoices_and_work_items
Revises: 0023_add_binder_intakes
Create Date: 2026-03-17

Changes:
- vat_invoices: add rate_type, deduction_rate, document_type, is_exceptional
- vat_work_items: add submission_reference, is_amendment, amends_item_id
"""

from alembic import op
import sqlalchemy as sa

revision = "0024_extend_vat_invoices_and_work_items"
down_revision = "0023_add_binder_intakes"
branch_labels = None
depends_on = None

vat_rate_type_enum = sa.Enum(
    "standard", "exempt", "zero_rate", name="vatratedtype"
)
document_type_enum = sa.Enum(
    "tax_invoice", "transaction_invoice", "receipt", "consolidated", "self_invoice",
    name="documenttype",
)


def upgrade() -> None:
    # ── vat_invoices ─────────────────────────────────────────────────────────
    op.add_column("vat_invoices", sa.Column("rate_type", sa.String(9), nullable=False, server_default="standard"))
    op.add_column("vat_invoices", sa.Column("deduction_rate", sa.Numeric(5, 4), nullable=False, server_default="1.0000"))
    op.add_column("vat_invoices", sa.Column("document_type", sa.String(19), nullable=True))
    op.add_column("vat_invoices", sa.Column("is_exceptional", sa.Boolean(), nullable=False, server_default=sa.false()))

    # ── vat_work_items ───────────────────────────────────────────────────────
    op.add_column("vat_work_items", sa.Column("submission_reference", sa.String(100), nullable=True))
    op.add_column("vat_work_items", sa.Column("is_amendment", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("vat_work_items", sa.Column("amends_item_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("vat_work_items", "amends_item_id")
    op.drop_column("vat_work_items", "is_amendment")
    op.drop_column("vat_work_items", "submission_reference")
    op.drop_column("vat_invoices", "is_exceptional")
    op.drop_column("vat_invoices", "document_type")
    op.drop_column("vat_invoices", "deduction_rate")
    op.drop_column("vat_invoices", "rate_type")
