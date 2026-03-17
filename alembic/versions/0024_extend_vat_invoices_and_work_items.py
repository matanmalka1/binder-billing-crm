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
    with op.batch_alter_table("vat_invoices") as batch_op:
        batch_op.add_column(
            sa.Column(
                "rate_type",
                sa.Enum("standard", "exempt", "zero_rate", name="vatratedtype"),
                nullable=False,
                server_default="standard",
            )
        )
        batch_op.add_column(
            sa.Column(
                "deduction_rate",
                sa.Numeric(5, 4),
                nullable=False,
                server_default="1.0000",
            )
        )
        batch_op.add_column(
            sa.Column(
                "document_type",
                sa.Enum(
                    "tax_invoice",
                    "transaction_invoice",
                    "receipt",
                    "consolidated",
                    "self_invoice",
                    name="documenttype",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_exceptional",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    # ── vat_work_items ───────────────────────────────────────────────────────
    with op.batch_alter_table("vat_work_items") as batch_op:
        batch_op.add_column(
            sa.Column("submission_reference", sa.String(100), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_amendment",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "amends_item_id",
                sa.Integer(),
                sa.ForeignKey("vat_work_items.id"),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("vat_work_items") as batch_op:
        batch_op.drop_column("amends_item_id")
        batch_op.drop_column("is_amendment")
        batch_op.drop_column("submission_reference")

    with op.batch_alter_table("vat_invoices") as batch_op:
        batch_op.drop_column("is_exceptional")
        batch_op.drop_column("document_type")
        batch_op.drop_column("deduction_rate")
        batch_op.drop_column("rate_type")
