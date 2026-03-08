"""add credit_points to annual_report_details

Revision ID: 0007_add_credit_points_to_annual_report_detail
Revises: 0006_annual_report_income_expense_and_fks
Create Date: 2026-03-08 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007_add_credit_points_to_annual_report_detail'
down_revision: Union[str, Sequence[str], None] = '0006_annual_report_income_expense_and_fks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'annual_report_details',
        sa.Column('credit_points', sa.Numeric(5, 2), nullable=True, server_default='2.25'),
    )


def downgrade() -> None:
    op.drop_column('annual_report_details', 'credit_points')
