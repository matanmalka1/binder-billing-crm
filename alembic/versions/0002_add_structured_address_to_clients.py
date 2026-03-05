"""add structured address fields to clients

Revision ID: 0002_structured_address
Revises:
Create Date: 2026-03-05

Replaces the single free-text `address` column on the `clients` table
with five structured address fields:
  - address_street
  - address_building_number
  - address_apartment
  - address_city
  - address_zip_code

The legacy `address` column is kept (nullable) to preserve any existing
data during migration.  A future migration can drop it once all rows
have been migrated to the structured fields.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0002_structured_address"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("address_street", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("address_building_number", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("address_apartment", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("address_city", sa.String(), nullable=True))
    op.add_column("clients", sa.Column("address_zip_code", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "address_zip_code")
    op.drop_column("clients", "address_city")
    op.drop_column("clients", "address_apartment")
    op.drop_column("clients", "address_building_number")
    op.drop_column("clients", "address_street")
