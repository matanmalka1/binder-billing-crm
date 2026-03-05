"""remove business_sector from clients

Revision ID: 0003_remove_business_sector
Revises: 0002_structured_address
Create Date: 2026-03-05

Removes the redundant `business_sector` column from the `clients` table.
Occupation/business type is owned exclusively by `client_tax_profiles.business_type`.
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_remove_business_sector"
down_revision = "0002_structured_address"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("clients", "business_sector")


def downgrade() -> None:
    op.add_column("clients", sa.Column("business_sector", sa.String(), nullable=True))