"""pivot_authority_contacts_to_client_scope

Revision ID: 5a9255230515
Revises: 168f26261f37
Create Date: 2026-04-09 13:51:05.639515

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a9255230515'
down_revision: Union[str, Sequence[str], None] = '168f26261f37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    ac_cols = {c['name'] for c in inspector.get_columns('authority_contacts')}
    ac_indexes = {i['name'] for i in inspector.get_indexes('authority_contacts')}

    # Drop the many-to-many link table if it still exists
    if 'authority_contact_links' in existing_tables:
        for idx in inspector.get_indexes('authority_contact_links'):
            op.drop_index(idx['name'], table_name='authority_contact_links')
        op.drop_table('authority_contact_links')

    # Pivot authority_contacts: business_id → client_id.
    # Use batch mode (required for SQLite FK/column changes).
    # Skip steps already applied (dev DB auto-migrated via create_all).
    needs_recreate = 'business_id' in ac_cols or 'client_id' not in ac_cols

    if needs_recreate:
        # Drop old business_id indexes before batch_alter so recreate='always'
        # does not attempt to copy them into the new table schema.
        for old_idx in ('idx_authority_contact_business', 'ix_authority_contacts_business_id'):
            if old_idx in ac_indexes:
                op.drop_index(old_idx, table_name='authority_contacts')

        with op.batch_alter_table('authority_contacts', recreate='always') as batch_op:
            if 'client_id' not in ac_cols:
                batch_op.add_column(sa.Column('client_id', sa.Integer(), nullable=True))
            if 'business_id' in ac_cols:
                batch_op.drop_column('business_id')
            batch_op.alter_column('client_id', nullable=False)
            batch_op.create_foreign_key(
                'fk_authority_contacts_client_id', 'clients', ['client_id'], ['id']
            )
            if 'idx_authority_contact_client' not in ac_indexes:
                batch_op.create_index('idx_authority_contact_client', ['client_id'], unique=False)
            if 'ix_authority_contacts_client_id' not in ac_indexes:
                batch_op.create_index(
                    op.f('ix_authority_contacts_client_id'), ['client_id'], unique=False
                )


def downgrade() -> None:
    with op.batch_alter_table('authority_contacts', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('business_id', sa.INTEGER(), nullable=True))
        batch_op.drop_column('client_id')
        batch_op.alter_column('business_id', nullable=False)
        batch_op.create_foreign_key(
            'fk_authority_contacts_business_id', 'businesses', ['business_id'], ['id']
        )
        batch_op.create_index('idx_authority_contact_business', ['business_id'], unique=False)
        batch_op.create_index(
            op.f('ix_authority_contacts_business_id'), ['business_id'], unique=False
        )

    op.create_table(
        'authority_contact_links',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('contact_id', sa.INTEGER(), nullable=False),
        sa.Column('client_id', sa.INTEGER(), nullable=False),
        sa.Column('business_id', sa.INTEGER(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['authority_contacts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'contact_id', 'client_id', 'business_id', name='uq_authority_contact_link'
        ),
    )
