"""drop annual report detail credit cache

Revision ID: 0005_drop_annual_report_detail_credit_cache
Revises: 0004_remove_annual_report_type_and_shrink_form_enum
Create Date: 2026-04-14

Changes:
- Drop derived credit-point cache columns from annual_report_details
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_drop_annual_report_detail_credit_cache"
down_revision: Union[str, Sequence[str], None] = "0004_remove_annual_report_type_and_shrink_form_enum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("annual_report_details", schema=None) as batch_op:
        batch_op.drop_column("credit_points")
        batch_op.drop_column("pension_credit_points")
        batch_op.drop_column("life_insurance_credit_points")
        batch_op.drop_column("tuition_credit_points")


def downgrade() -> None:
    with op.batch_alter_table("annual_report_details", schema=None) as batch_op:
        batch_op.add_column(sa.Column("credit_points", sa.Numeric(precision=5, scale=2), nullable=True))
        batch_op.add_column(sa.Column("pension_credit_points", sa.Numeric(precision=5, scale=2), nullable=True))
        batch_op.add_column(sa.Column("life_insurance_credit_points", sa.Numeric(precision=5, scale=2), nullable=True))
        batch_op.add_column(sa.Column("tuition_credit_points", sa.Numeric(precision=5, scale=2), nullable=True))
