"""domain_refactor_tax_entity

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-07 19:00:00.000000

Major domain refactor: TaxEntity / BusinessActivity split.

Changes:
1. Add entity_type + tax profile fields to clients table.
2. Copy data from business_tax_profiles to clients (dev only — last business wins).
3. Pivot vat_work_items from business_id → client_id.
4. Add business_activity_id to vat_invoices.
5. Backfill and enforce business_name NOT NULL in businesses.
6. Drop business_tax_profiles table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    # ── Step 1: Add new columns to clients ────────────────────────────────────
    existing_client_cols = {r[1] for r in bind.execute(sa.text("PRAGMA table_info(clients)")).fetchall()}
    new_client_cols = {
        'entity_type': sa.Column('entity_type', sa.String(50), nullable=True),
        'vat_start_date': sa.Column('vat_start_date', sa.Date(), nullable=True),
        'vat_exempt_ceiling': sa.Column('vat_exempt_ceiling', sa.Numeric(12, 0), nullable=True),
        'advance_rate': sa.Column('advance_rate', sa.Numeric(5, 2), nullable=True),
        'advance_rate_updated_at': sa.Column('advance_rate_updated_at', sa.Date(), nullable=True),
        'accountant_name': sa.Column('accountant_name', sa.String(100), nullable=True),
        'business_type_label': sa.Column('business_type_label', sa.String(100), nullable=True),
        'fiscal_year_start_month': sa.Column('fiscal_year_start_month', sa.Integer(),
                                             nullable=False, server_default='1'),
        'tax_year_start': sa.Column('tax_year_start', sa.Integer(), nullable=True),
    }
    for col_name, col_def in new_client_cols.items():
        if col_name not in existing_client_cols:
            op.add_column('clients', col_def)

    # ── Step 2: Copy data from business_tax_profiles to clients ───────────────
    # Check if business_tax_profiles table exists before querying it
    result = session.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='business_tax_profiles'"
    )).fetchone()

    if result:
        profiles = session.execute(sa.text(
            "SELECT btp.business_id, btp.vat_start_date, btp.vat_exempt_ceiling, "
            "btp.advance_rate, btp.advance_rate_updated_at, btp.accountant_name, "
            "btp.business_type, btp.tax_year_start, btp.fiscal_year_start_month, "
            "b.client_id "
            "FROM business_tax_profiles btp "
            "JOIN businesses b ON b.id = btp.business_id "
            "ORDER BY btp.id"
        )).fetchall()

        for row in profiles:
            session.execute(sa.text(
                "UPDATE clients SET "
                "vat_start_date = :vat_start_date, "
                "vat_exempt_ceiling = :vat_exempt_ceiling, "
                "advance_rate = :advance_rate, "
                "advance_rate_updated_at = :advance_rate_updated_at, "
                "accountant_name = :accountant_name, "
                "business_type_label = :business_type, "
                "tax_year_start = :tax_year_start, "
                "fiscal_year_start_month = COALESCE(:fiscal_year_start_month, 1) "
                "WHERE id = :client_id"
            ), {
                "vat_start_date": row.vat_start_date,
                "vat_exempt_ceiling": row.vat_exempt_ceiling,
                "advance_rate": row.advance_rate,
                "advance_rate_updated_at": row.advance_rate_updated_at,
                "accountant_name": row.accountant_name,
                "business_type": row.business_type,
                "tax_year_start": row.tax_year_start,
                "fiscal_year_start_month": row.fiscal_year_start_month,
                "client_id": row.client_id,
            })

        session.commit()

    # ── Step 3: Pivot vat_work_items from business_id → client_id ─────────────
    vwi_cols = {r[1] for r in bind.execute(sa.text("PRAGMA table_info(vat_work_items)")).fetchall()}

    if 'client_id' not in vwi_cols:
        # Add client_id column (nullable first for backfill)
        op.add_column('vat_work_items',
                      sa.Column('client_id', sa.Integer(), nullable=True))

    if 'business_id' in vwi_cols:
        # Backfill client_id from businesses
        session.execute(sa.text(
            "UPDATE vat_work_items "
            "SET client_id = (SELECT client_id FROM businesses WHERE businesses.id = vat_work_items.business_id) "
            "WHERE client_id IS NULL"
        ))
        session.commit()

        # SQLite: recreate the table without business_id
        # Get current columns excluding business_id
        session.execute(sa.text(
            "CREATE TABLE vat_work_items_new AS "
            "SELECT id, client_id, created_by, assigned_to, period, period_type, status, "
            "pending_materials_note, total_output_vat, total_input_vat, net_vat, "
            "total_output_net, total_input_net, final_vat_amount, is_overridden, "
            "override_justification, submission_method, filed_at, filed_by, "
            "submission_reference, is_amendment, amends_item_id, created_at, updated_at, "
            "deleted_at, deleted_by FROM vat_work_items"
        ))
        session.execute(sa.text("DROP TABLE vat_work_items"))
        session.execute(sa.text(
            "CREATE TABLE vat_work_items ("
            "id INTEGER NOT NULL PRIMARY KEY, "
            "client_id INTEGER NOT NULL REFERENCES clients(id), "
            "created_by INTEGER REFERENCES users(id), "
            "assigned_to INTEGER REFERENCES users(id), "
            "period VARCHAR NOT NULL, "
            "period_type VARCHAR NOT NULL, "
            "status VARCHAR NOT NULL, "
            "pending_materials_note VARCHAR, "
            "total_output_vat NUMERIC, "
            "total_input_vat NUMERIC, "
            "net_vat NUMERIC, "
            "total_output_net NUMERIC, "
            "total_input_net NUMERIC, "
            "final_vat_amount NUMERIC, "
            "is_overridden BOOLEAN NOT NULL DEFAULT 0, "
            "override_justification VARCHAR, "
            "submission_method VARCHAR, "
            "filed_at DATETIME, "
            "filed_by INTEGER REFERENCES users(id), "
            "submission_reference VARCHAR, "
            "is_amendment BOOLEAN NOT NULL DEFAULT 0, "
            "amends_item_id INTEGER REFERENCES vat_work_items(id), "
            "created_at DATETIME NOT NULL, "
            "updated_at DATETIME, "
            "deleted_at DATETIME, "
            "deleted_by INTEGER REFERENCES users(id)"
            ")"
        ))
        session.execute(sa.text(
            "INSERT INTO vat_work_items SELECT * FROM vat_work_items_new"
        ))
        session.execute(sa.text("DROP TABLE vat_work_items_new"))
        session.commit()

        bind.execute(sa.text(
            "CREATE INDEX ix_vat_work_items_client_id ON vat_work_items (client_id)"
        ))
        bind.execute(sa.text(
            "CREATE UNIQUE INDEX uq_vat_work_item_client_period ON vat_work_items (client_id, period) "
            "WHERE deleted_at IS NULL"
        ))
        session.commit()

    # ── Step 4: Add business_activity_id to vat_invoices ─────────────────────
    vi_cols = {r[1] for r in bind.execute(sa.text("PRAGMA table_info(vat_invoices)")).fetchall()}
    if 'business_activity_id' not in vi_cols:
        op.add_column('vat_invoices',
                      sa.Column('business_activity_id', sa.Integer(), nullable=True))
        op.create_index('ix_vat_invoices_business_activity', 'vat_invoices', ['business_activity_id'])

    # ── Step 5: Backfill business_name NOT NULL in businesses ─────────────────
    session.execute(sa.text(
        "UPDATE businesses "
        "SET business_name = (SELECT full_name FROM clients WHERE clients.id = businesses.client_id) "
        "WHERE business_name IS NULL"
    ))
    session.commit()

    # business_name is already NOT NULL in most schemas; skip if column already not null
    biz_col_info = {r[1]: r for r in bind.execute(sa.text("PRAGMA table_info(businesses)")).fetchall()}
    if biz_col_info.get('business_name') and biz_col_info['business_name'][3] == 0:
        # notnull=0 means nullable; use batch_alter to enforce NOT NULL
        with op.batch_alter_table('businesses', recreate='always') as batch_op:
            batch_op.alter_column('business_name', existing_type=sa.String(200), nullable=False)

    # ── Step 6: Drop business_tax_profiles table ──────────────────────────────
    result = session.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='business_tax_profiles'"
    )).fetchone()
    if result:
        op.drop_table('business_tax_profiles')


def downgrade() -> None:
    """Best-effort downgrade for development use only."""
    bind = op.get_bind()
    session = Session(bind=bind)

    # Recreate business_tax_profiles
    op.create_table(
        'business_tax_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('vat_type', sa.String(20), nullable=True),
        sa.Column('vat_start_date', sa.Date(), nullable=True),
        sa.Column('accountant_name', sa.String(100), nullable=True),
        sa.Column('vat_exempt_ceiling', sa.Numeric(12, 0), nullable=True),
        sa.Column('advance_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('advance_rate_updated_at', sa.Date(), nullable=True),
        sa.Column('business_type', sa.String(100), nullable=True),
        sa.Column('tax_year_start', sa.Integer(), nullable=True),
        sa.Column('fiscal_year_start_month', sa.Integer(), nullable=False,
                  server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Restore business_name nullable
    with op.batch_alter_table('businesses') as batch_op:
        batch_op.alter_column('business_name', nullable=True)

    # Drop vat_invoices additions
    op.drop_index('ix_vat_invoices_business_activity', table_name='vat_invoices')
    op.drop_column('vat_invoices', 'business_activity_id')

    # Restore vat_work_items business_id
    op.add_column('vat_work_items',
                  sa.Column('business_id', sa.Integer(), nullable=True))
    session.execute(sa.text(
        "UPDATE vat_work_items "
        "SET business_id = (SELECT b.id FROM businesses b WHERE b.client_id = vat_work_items.client_id LIMIT 1) "
        "WHERE business_id IS NULL"
    ))
    session.commit()

    with op.batch_alter_table('vat_work_items') as batch_op:
        batch_op.alter_column('business_id', nullable=False)
        batch_op.drop_index('uq_vat_work_item_client_period')
        batch_op.drop_index('ix_vat_work_items_client_id')
        batch_op.drop_column('client_id')

    # Drop new client columns
    for col in ['entity_type', 'vat_start_date', 'vat_exempt_ceiling', 'advance_rate',
                'advance_rate_updated_at', 'accountant_name', 'business_type_label',
                'fiscal_year_start_month', 'tax_year_start']:
        op.drop_column('clients', col)
