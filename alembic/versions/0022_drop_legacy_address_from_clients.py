"""drop legacy address from clients

Revision ID: 0022_drop_legacy_address_from_clients
Revises: 0021_extend_permanent_documents
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa

revision = "0022_drop_legacy_address_from_clients"
down_revision = "0021_extend_permanent_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("clients", "address")


def downgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("address", sa.String(), nullable=True),
    )
