"""annual report income/expense lines and cross-domain FKs

Revision ID: 0006_annual_report_income_expense_and_fks
Revises: 0005_add_updated_at_to_clients
Create Date: 2026-03-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006_annual_report_income_expense_and_fks'
down_revision: Union[str, Sequence[str], None] = '0005_add_updated_at_to_clients'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Income line items ────────────────────────────────────────────────────
    op.create_table(
        'annual_report_income_lines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('annual_report_id', sa.Integer(), nullable=False),
        sa.Column(
            'source_type',
            sa.Enum(
                'business', 'salary', 'interest', 'dividends', 'capital_gains',
                'rental', 'foreign', 'pension', 'other',
                name='incomesourcetype',
            ),
            nullable=False,
        ),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['annual_report_id'], ['annual_reports.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_income_line_report',
        'annual_report_income_lines',
        ['annual_report_id'],
    )

    # ── Expense line items ───────────────────────────────────────────────────
    op.create_table(
        'annual_report_expense_lines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('annual_report_id', sa.Integer(), nullable=False),
        sa.Column(
            'category',
            sa.Enum(
                'office_rent', 'professional_services', 'salaries', 'depreciation',
                'vehicle', 'marketing', 'insurance', 'communication', 'travel',
                'training', 'bank_fees', 'other',
                name='expensecategorytype',
            ),
            nullable=False,
        ),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['annual_report_id'], ['annual_reports.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_expense_line_report',
        'annual_report_expense_lines',
        ['annual_report_id'],
    )

    # ── annual_report_id FK on charges ───────────────────────────────────────
    op.add_column(
        'charges',
        sa.Column('annual_report_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_charges_annual_report',
        'charges', 'annual_reports',
        ['annual_report_id'], ['id'],
    )
    op.create_index('idx_charge_annual_report', 'charges', ['annual_report_id'])

    # ── annual_report_id FK on binders ───────────────────────────────────────
    op.add_column(
        'binders',
        sa.Column('annual_report_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_binders_annual_report',
        'binders', 'annual_reports',
        ['annual_report_id'], ['id'],
    )
    op.create_index('idx_binder_annual_report', 'binders', ['annual_report_id'])

    # ── annual_report_id FK on reminders ─────────────────────────────────────
    op.add_column(
        'reminders',
        sa.Column('annual_report_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_reminders_annual_report',
        'reminders', 'annual_reports',
        ['annual_report_id'], ['id'],
    )
    op.create_index('idx_reminder_annual_report', 'reminders', ['annual_report_id'])


def downgrade() -> None:
    op.drop_index('idx_reminder_annual_report', table_name='reminders')
    op.drop_constraint('fk_reminders_annual_report', 'reminders', type_='foreignkey')
    op.drop_column('reminders', 'annual_report_id')

    op.drop_index('idx_binder_annual_report', table_name='binders')
    op.drop_constraint('fk_binders_annual_report', 'binders', type_='foreignkey')
    op.drop_column('binders', 'annual_report_id')

    op.drop_index('idx_charge_annual_report', table_name='charges')
    op.drop_constraint('fk_charges_annual_report', 'charges', type_='foreignkey')
    op.drop_column('charges', 'annual_report_id')

    op.drop_index('idx_expense_line_report', table_name='annual_report_expense_lines')
    op.drop_table('annual_report_expense_lines')

    op.drop_index('idx_income_line_report', table_name='annual_report_income_lines')
    op.drop_table('annual_report_income_lines')
