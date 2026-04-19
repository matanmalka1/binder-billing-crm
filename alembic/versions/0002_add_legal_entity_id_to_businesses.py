"""add_legal_entity_id_to_businesses

Revision ID: 0002_add_legal_entity_id_to_businesses
Revises: bce6996cfcd8
Create Date: 2026-04-19

Additive only: adds legal_entity_id FK to businesses. client_id retained.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_legal_entity_id_to_businesses"
down_revision: Union[str, None] = "bce6996cfcd8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("legal_entity_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_businesses_legal_entity_id",
        "businesses",
        "legal_entities",
        ["legal_entity_id"],
        ["id"],
    )
    op.create_index(
        "ix_business_legal_entity_id",
        "businesses",
        ["legal_entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_business_legal_entity_id", table_name="businesses")
    op.drop_constraint("fk_businesses_legal_entity_id", "businesses", type_="foreignkey")
    op.drop_column("businesses", "legal_entity_id")
