"""add business_type and tax_year_start to business_tax_profiles

Revision ID: 5d8f1a4c2e7b
Revises: 4c9d2e3b1f6a
Create Date: 2026-03-25

Adds business_type (varchar) and tax_year_start (integer) columns to
business_tax_profiles table, exposing them via the tax profile API.
"""

from alembic import op
import sqlalchemy as sa

revision = "5d8f1a4c2e7b"
down_revision = "4c9d2e3b1f6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "business_tax_profiles",
        sa.Column("business_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "business_tax_profiles",
        sa.Column("tax_year_start", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("business_tax_profiles", "tax_year_start")
    op.drop_column("business_tax_profiles", "business_type")
