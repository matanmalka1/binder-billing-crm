"""Add advance payment calculation fields.

Replace reported_turnover/turnover_source_vat_work_item_id with
turnover_amount, advance_rate, calculated_amount, override_amount.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_advance_payment_calculation_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "ix_advance_payments_turnover_source_vat_work_item_id",
        table_name="advance_payments",
    )
    op.drop_constraint(
        "advance_payments_turnover_source_vat_work_item_id_fkey",
        "advance_payments",
        type_="foreignkey",
    )
    op.drop_column("advance_payments", "turnover_source_vat_work_item_id")
    op.drop_column("advance_payments", "reported_turnover")

    op.add_column(
        "advance_payments",
        sa.Column("turnover_amount", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "advance_payments",
        sa.Column("advance_rate", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "advance_payments",
        sa.Column("calculated_amount", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "advance_payments",
        sa.Column("override_amount", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("advance_payments", "override_amount")
    op.drop_column("advance_payments", "calculated_amount")
    op.drop_column("advance_payments", "advance_rate")
    op.drop_column("advance_payments", "turnover_amount")

    op.add_column(
        "advance_payments",
        sa.Column("reported_turnover", sa.Numeric(precision=14, scale=2), nullable=True),
    )
    op.add_column(
        "advance_payments",
        sa.Column("turnover_source_vat_work_item_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "advance_payments_turnover_source_vat_work_item_id_fkey",
        "advance_payments",
        "vat_work_items",
        ["turnover_source_vat_work_item_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_advance_payments_turnover_source_vat_work_item_id"),
        "advance_payments",
        ["turnover_source_vat_work_item_id"],
        unique=False,
    )
