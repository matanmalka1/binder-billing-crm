"""Fix upper() casts on vat_invoice enum columns for PostgreSQL

Revision ID: 0028_fix_enum_upper_cast
Revises: 0027_fix_client_id_number_unique_constraint
Create Date: 2026-03-17

Migration 0026 called upper(col) directly on native PostgreSQL enum columns,
which fails because upper() requires text input. This migration casts each
column to text, uppercases it, then casts back to the correct enum type.
Skipped on SQLite (dev) where enums are stored as plain strings.
"""

from alembic import op

revision = "0028_fix_enum_upper_cast"
down_revision = "0027_fix_client_id_number_unique_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        "UPDATE vat_invoices "
        "SET invoice_type = upper(invoice_type::text)::invoicetype"
    )
    op.execute(
        "UPDATE vat_invoices "
        "SET expense_category = upper(expense_category::text)::expensecategory "
        "WHERE expense_category IS NOT NULL"
    )
    op.execute(
        "UPDATE vat_invoices "
        "SET rate_type = upper(rate_type::text)::vatratetype "
        "WHERE rate_type IS NOT NULL"
    )
    op.execute(
        "UPDATE vat_invoices "
        "SET document_type = upper(document_type::text)::documenttype "
        "WHERE document_type IS NOT NULL"
    )


def downgrade() -> None:
    pass
