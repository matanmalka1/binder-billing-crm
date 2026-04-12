"""advance_payments_pivot_to_client_id

Revision ID: 0022
Revises: 5a9255230515
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: Union[str, Sequence[str], None] = "5a9255230515"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add client_id column (nullable for now to allow backfill)
    op.add_column(
        "advance_payments",
        sa.Column("client_id", sa.Integer(), nullable=True),
    )

    # 2. Backfill client_id from the business FK
    op.execute(
        """
        UPDATE advance_payments
        SET client_id = businesses.client_id
        FROM businesses
        WHERE advance_payments.business_id = businesses.id
        """
    )

    # 3. Make client_id non-nullable and add FK
    op.alter_column("advance_payments", "client_id", nullable=False)
    op.create_foreign_key(
        "fk_advance_payments_client_id",
        "advance_payments",
        "clients",
        ["client_id"],
        ["id"],
    )
    op.create_index(
        "idx_advance_payment_client_period",
        "advance_payments",
        ["client_id", "period"],
    )

    # 4. Create new unique constraint
    op.create_unique_constraint(
        "uq_advance_payment_client_period",
        "advance_payments",
        ["client_id", "period"],
    )

    # 5. Drop old business-scoped constraint, index, and FK
    op.drop_constraint(
        "uq_advance_payment_business_period",
        "advance_payments",
        type_="unique",
    )
    op.drop_index(
        "idx_advance_payment_business_period",
        table_name="advance_payments",
    )
    op.drop_constraint(
        "advance_payments_business_id_fkey",
        "advance_payments",
        type_="foreignkey",
    )

    # 6. Drop business_id column
    op.drop_column("advance_payments", "business_id")


def downgrade() -> None:
    # Re-add business_id (nullable — original data is lost)
    op.add_column(
        "advance_payments",
        sa.Column("business_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "advance_payments_business_id_fkey",
        "advance_payments",
        "businesses",
        ["business_id"],
        ["id"],
    )
    op.create_index(
        "idx_advance_payment_business_period",
        "advance_payments",
        ["business_id", "period"],
    )
    op.create_unique_constraint(
        "uq_advance_payment_business_period",
        "advance_payments",
        ["business_id", "period"],
    )

    # Drop client-scoped additions
    op.drop_constraint(
        "uq_advance_payment_client_period",
        "advance_payments",
        type_="unique",
    )
    op.drop_index(
        "idx_advance_payment_client_period",
        table_name="advance_payments",
    )
    op.drop_constraint(
        "fk_advance_payments_client_id",
        "advance_payments",
        type_="foreignkey",
    )
    op.drop_column("advance_payments", "client_id")
