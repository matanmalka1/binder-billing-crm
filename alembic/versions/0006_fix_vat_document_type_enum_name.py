"""fix vat_invoices document_type enum collision with permanent_documents

Revision ID: 6e3f2b1d0c8a
Revises: 5d8f1a4c2e7b
Create Date: 2026-03-29

The documenttype PostgreSQL enum was first created for permanent_documents
with values (id_copy, power_of_attorney, ...). vat_invoices.document_type
reused the same enum name, so its VAT-specific values (tax_invoice, etc.)
were never registered in the DB.

Fix: create a new vatdocumenttype enum with the correct VAT values and
alter the vat_invoices.document_type column to use it.
"""

from alembic import op
import sqlalchemy as sa

revision = "6e3f2b1d0c8a"
down_revision = "5d8f1a4c2e7b"
branch_labels = None
depends_on = None

VAT_DOC_TYPE_VALUES = [
    "tax_invoice",
    "transaction_invoice",
    "receipt",
    "consolidated",
    "self_invoice",
    "credit_note",
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    vatdocumenttype = sa.Enum(*VAT_DOC_TYPE_VALUES, name="vatdocumenttype")
    vatdocumenttype.create(bind, checkfirst=True)

    op.alter_column(
        "vat_invoices",
        "document_type",
        type_=vatdocumenttype,
        existing_nullable=True,
        postgresql_using="document_type::text::vatdocumenttype",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Revert column back to the legacy (incorrect) documenttype enum
    legacy_documenttype = sa.Enum(
        "id_copy", "power_of_attorney", "engagement_agreement", "tax_form",
        "receipt", "invoice_doc", "bank_approval", "withholding_certificate",
        "nii_approval", "other",
        name="documenttype",
    )

    op.alter_column(
        "vat_invoices",
        "document_type",
        type_=legacy_documenttype,
        existing_nullable=True,
        postgresql_using="NULL::documenttype",
    )

    sa.Enum(name="vatdocumenttype").drop(bind, checkfirst=True)
