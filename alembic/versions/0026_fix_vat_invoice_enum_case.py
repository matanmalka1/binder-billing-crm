"""re-uppercase vat_invoice enum columns for prod (0025 had broken casts)

Revision ID: 0026_fix_vat_invoice_enum_case
Revises: 0025_normalize_vat_invoice_enum_case
Create Date: 2026-03-17

Migration 0025 used ::invoicetype / ::expensecategory PostgreSQL casts that
don't exist, so those UPDATE statements failed on prod and left the values
lowercase. This migration re-runs the correct upper() without any type cast.
Also covers document_type which was added in 0024 with lowercase defaults.
"""

from alembic import op

revision = "0026_fix_vat_invoice_enum_case"
down_revision = "0025_normalize_vat_invoice_enum_case"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        "UPDATE vat_invoices SET invoice_type = upper(invoice_type::text)::invoicetype"
    )
    op.execute(
        "UPDATE vat_invoices SET expense_category = upper(expense_category::text)::expensecategory "
        "WHERE expense_category IS NOT NULL"
    )
    op.execute(
        "UPDATE vat_invoices SET rate_type = upper(rate_type::text)::vatratedtype "
        "WHERE rate_type IS NOT NULL"
    )
    op.execute(
        "UPDATE vat_invoices SET document_type = upper(document_type::text)::documenttype "
        "WHERE document_type IS NOT NULL"
    )


def downgrade() -> None:
    pass
