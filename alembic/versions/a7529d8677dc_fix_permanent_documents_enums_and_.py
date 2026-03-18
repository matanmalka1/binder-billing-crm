"""fix: permanent_documents enums and annual_report partial index

Revision ID: a7529d8677dc
Revises: 0001_initial_schema
Create Date: 2026-03-18 11:48:25.356810
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7529d8677dc'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # ── permanent_documents: String → pg_enum (PostgreSQL only) ───────────────
    if is_postgresql():
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'documenttype') THEN
                    CREATE TYPE documenttype AS ENUM (
                        'id_copy', 'power_of_attorney', 'engagement_agreement',
                        'tax_form', 'receipt', 'invoice_doc', 'bank_approval',
                        'withholding_certificate', 'nii_approval', 'other'
                    );
                END IF;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'documentstatus') THEN
                    CREATE TYPE documentstatus AS ENUM (
                        'pending', 'received', 'approved', 'rejected'
                    );
                END IF;
            END $$;
        """)
        op.execute("""
            ALTER TABLE permanent_documents
                ALTER COLUMN document_type TYPE documenttype
                    USING document_type::documenttype,
                ALTER COLUMN status TYPE documentstatus
                    USING status::documentstatus;
        """)

    # ── indexes ───────────────────────────────────────────────────────────────
    op.drop_index(op.f('ix_client_tax_profiles_client_id'), table_name='client_tax_profiles')
    op.create_index(op.f('ix_client_tax_profiles_client_id'), 'client_tax_profiles', ['client_id'], unique=True)

    op.drop_index(op.f('ix_clients_id_number_active'), table_name='clients')
    op.create_index('ix_clients_id_number_active', 'clients', ['id_number'], unique=True,
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index(op.f('ix_clients_id_number'), 'clients', ['id_number'], unique=False)

    op.create_index(op.f('ix_correspondence_entries_client_id'), 'correspondence_entries', ['client_id'], unique=False)

    op.drop_index(op.f('ix_invoices_charge_id'), table_name='invoices')
    op.create_index(op.f('ix_invoices_charge_id'), 'invoices', ['charge_id'], unique=True)

    op.create_index(op.f('ix_signature_requests_annual_report_id'), 'signature_requests', ['annual_report_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_signature_requests_annual_report_id'), table_name='signature_requests')
    op.drop_index(op.f('ix_invoices_charge_id'), table_name='invoices')
    op.create_index(op.f('ix_invoices_charge_id'), 'invoices', ['charge_id'], unique=False)
    op.drop_index(op.f('ix_correspondence_entries_client_id'), table_name='correspondence_entries')
    op.drop_index(op.f('ix_clients_id_number'), table_name='clients')
    op.drop_index('ix_clients_id_number_active', table_name='clients',
                  postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index(op.f('ix_clients_id_number_active'), 'clients', ['id_number'], unique=False)
    op.drop_index(op.f('ix_client_tax_profiles_client_id'), table_name='client_tax_profiles')
    op.create_index(op.f('ix_client_tax_profiles_client_id'), 'client_tax_profiles', ['client_id'], unique=False)

    if is_postgresql():
        op.execute("""
            ALTER TABLE permanent_documents
                ALTER COLUMN document_type TYPE VARCHAR USING document_type::text,
                ALTER COLUMN status TYPE VARCHAR USING status::text;
        """)
        op.execute("DROP TYPE IF EXISTS documenttype;")
        op.execute("DROP TYPE IF EXISTS documentstatus;")
