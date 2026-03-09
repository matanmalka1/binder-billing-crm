"""add annual_report_id to advance_payments

Revision ID: 0008_add_annual_report_id_to_advance_payments
Revises: 0007_add_credit_points_to_annual_report_detail
Create Date: 2026-03-08 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '0008_add_annual_report_id_to_advance_payments'
down_revision: Union[str, Sequence[str], None] = '0007_add_credit_points_to_annual_report_detail'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    existing_cols = [c["name"] for c in insp.get_columns("advance_payments")]

    if "annual_report_id" not in existing_cols:
        op.add_column(
            'advance_payments',
            sa.Column('annual_report_id', sa.Integer(), nullable=True),
        )

    if not _is_sqlite():
        op.create_foreign_key(
            'fk_advance_payments_annual_report',
            'advance_payments', 'annual_reports',
            ['annual_report_id'], ['id'],
        )

    existing_indexes = [i["name"] for i in insp.get_indexes("advance_payments")]
    if "idx_advance_payment_annual_report" not in existing_indexes:
        op.create_index(
            'idx_advance_payment_annual_report',
            'advance_payments',
            ['annual_report_id'],
        )


def downgrade() -> None:
    op.drop_index('idx_advance_payment_annual_report', table_name='advance_payments')
    if not _is_sqlite():
        op.drop_constraint(
            'fk_advance_payments_annual_report', 'advance_payments', type_='foreignkey'
        )
    op.drop_column('advance_payments', 'annual_report_id')
