"""normalize vat_invoice enum columns to uppercase

Revision ID: 0025_normalize_vat_invoice_enum_case
Revises: 0024_extend_vat_invoices_and_work_items
Create Date: 2026-03-17

SQLAlchemy's Enum(PythonEnumClass) maps to enum member *names* (uppercase), not
string *values*. Migration 0024 added rate_type with server_default='standard'
(lowercase), which SQLAlchemy cannot deserialise. This migration uppercases all
three enum columns so they match SQLAlchemy's expected names.
"""

from alembic import op

revision = "0025_normalize_vat_invoice_enum_case"
down_revision = "0024_extend_vat_invoices_and_work_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE vat_invoices SET invoice_type = upper(invoice_type)")
    op.execute(
        "UPDATE vat_invoices SET expense_category = upper(expense_category) "
        "WHERE expense_category IS NOT NULL"
    )
    op.execute(
        "UPDATE vat_invoices SET rate_type = upper(rate_type) "
        "WHERE rate_type IS NOT NULL"
    )


def downgrade() -> None:
    pass
