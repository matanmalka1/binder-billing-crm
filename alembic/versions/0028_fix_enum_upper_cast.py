"""Fix upper() casts on vat_invoice enum columns for PostgreSQL

Revision ID: 0028_fix_enum_upper_cast
Revises: 0027_fix_client_id_number_unique_constraint
Create Date: 2026-03-17

All vat_invoice enum columns are plain VARCHAR — no native PG enum types exist.
Re-runs upper() to ensure values are uppercase after any prior failed migrations.
Idempotent: safe to run on already-uppercased values.
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

    op.execute("UPDATE vat_invoices SET invoice_type = upper(invoice_type)")
    op.execute(
        "UPDATE vat_invoices "
        "SET expense_category = upper(expense_category) "
        "WHERE expense_category IS NOT NULL"
    )
    op.execute(
        "UPDATE vat_invoices "
        "SET rate_type = upper(rate_type) "
        "WHERE rate_type IS NOT NULL"
    )
    op.execute(
        "UPDATE vat_invoices "
        "SET document_type = upper(document_type) "
        "WHERE document_type IS NOT NULL"
    )


def downgrade() -> None:
    pass
