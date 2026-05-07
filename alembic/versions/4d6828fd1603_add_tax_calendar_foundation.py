"""add tax calendar foundation

Revision ID: 4d6828fd1603
Revises: 9ecbb3d5f408
Create Date: 2026-05-07 13:59:04.520893

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 4d6828fd1603
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 9ecbb3d5f408

Notes:
- Adds the foundational tax-calendar models per Decision Doc v3 (Phase A, additive only):
  `deadline_rules` (versioned regulatory rules) and `tax_calendar_entries`
  (per-period regulatory facts shared across clients).
- Introduces two new PG enums: `deadlineruletype` and `obligationtype`.
  Names do not collide with existing TaxDeadline enums (`deadlinetype`,
  `taxdeadlinestatus`, `urgencylevel`).
- Partial unique indexes use `sa.text(...)` for both PostgreSQL and SQLite.
- INV-11 (DeadlineRule overlap) is enforced in the service layer, not by DB
  constraint, so no exclusion constraint is added here.
- Foreign key `tax_calendar_entries.deadline_rule_id -> deadline_rules.id`
  is `ON DELETE RESTRICT`.
- Does not modify existing tables (TaxDeadline, AdvancePayment, VatWorkItem,
  AnnualReport).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d6828fd1603'
down_revision: Union[str, Sequence[str], None] = '9ecbb3d5f408'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'deadline_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'rule_type',
            sa.Enum(
                'vat_monthly', 'vat_bimonthly', 'advance_monthly',
                'advance_bimonthly', 'annual_report',
                name='deadlineruletype',
            ),
            nullable=False,
        ),
        sa.Column('due_day_of_month', sa.Integer(), nullable=False),
        sa.Column('offset_months', sa.Integer(), server_default='0', nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            'due_day_of_month BETWEEN 1 AND 31',
            name='ck_deadline_rule_due_day_range',
        ),
        sa.CheckConstraint(
            'effective_to IS NULL OR effective_to >= effective_from',
            name='ck_deadline_rule_effective_range',
        ),
        sa.CheckConstraint(
            'offset_months >= 0',
            name='ck_deadline_rule_offset_months_non_negative',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_deadline_rule_type_effective', 'deadline_rules',
        ['rule_type', 'effective_from'], unique=False,
    )
    op.create_index(
        op.f('ix_deadline_rules_rule_type'), 'deadline_rules',
        ['rule_type'], unique=False,
    )

    op.create_table(
        'tax_calendar_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'obligation_type',
            sa.Enum(
                'vat', 'advance_payment', 'annual_report', 'national_insurance',
                name='obligationtype',
            ),
            nullable=False,
        ),
        sa.Column('period', sa.String(length=7), nullable=True),
        sa.Column('period_months_count', sa.Integer(), nullable=True),
        sa.Column('tax_year', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('deadline_rule_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "(obligation_type = 'annual_report' AND period IS NULL) "
            "OR (obligation_type <> 'annual_report' AND period IS NOT NULL)",
            name='ck_tax_calendar_entry_period_nullability',
        ),
        sa.CheckConstraint(
            "(obligation_type = 'annual_report' AND period_months_count IS NULL) "
            "OR (obligation_type <> 'annual_report' "
            "    AND period_months_count IN (1, 2))",
            name='ck_tax_calendar_entry_months_count',
        ),
        sa.ForeignKeyConstraint(
            ['deadline_rule_id'], ['deadline_rules.id'], ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_tax_calendar_entries_deadline_rule_id'),
        'tax_calendar_entries', ['deadline_rule_id'], unique=False,
    )
    op.create_index(
        op.f('ix_tax_calendar_entries_due_date'),
        'tax_calendar_entries', ['due_date'], unique=False,
    )
    op.create_index(
        op.f('ix_tax_calendar_entries_obligation_type'),
        'tax_calendar_entries', ['obligation_type'], unique=False,
    )
    op.create_index(
        'uq_tax_calendar_entry_periodic', 'tax_calendar_entries',
        ['obligation_type', 'period', 'period_months_count'],
        unique=True,
        postgresql_where=sa.text("obligation_type <> 'annual_report'"),
        sqlite_where=sa.text("obligation_type <> 'annual_report'"),
    )
    op.create_index(
        'uq_tax_calendar_entry_annual', 'tax_calendar_entries',
        ['obligation_type', 'tax_year'],
        unique=True,
        postgresql_where=sa.text("obligation_type = 'annual_report'"),
        sqlite_where=sa.text("obligation_type = 'annual_report'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'uq_tax_calendar_entry_annual', table_name='tax_calendar_entries',
        postgresql_where=sa.text("obligation_type = 'annual_report'"),
        sqlite_where=sa.text("obligation_type = 'annual_report'"),
    )
    op.drop_index(
        'uq_tax_calendar_entry_periodic', table_name='tax_calendar_entries',
        postgresql_where=sa.text("obligation_type <> 'annual_report'"),
        sqlite_where=sa.text("obligation_type <> 'annual_report'"),
    )
    op.drop_index(
        op.f('ix_tax_calendar_entries_obligation_type'),
        table_name='tax_calendar_entries',
    )
    op.drop_index(
        op.f('ix_tax_calendar_entries_due_date'),
        table_name='tax_calendar_entries',
    )
    op.drop_index(
        op.f('ix_tax_calendar_entries_deadline_rule_id'),
        table_name='tax_calendar_entries',
    )
    op.drop_table('tax_calendar_entries')
    sa.Enum(name='obligationtype').drop(op.get_bind(), checkfirst=True)

    op.drop_index(
        op.f('ix_deadline_rules_rule_type'), table_name='deadline_rules',
    )
    op.drop_index(
        'idx_deadline_rule_type_effective', table_name='deadline_rules',
    )
    op.drop_table('deadline_rules')
    sa.Enum(name='deadlineruletype').drop(op.get_bind(), checkfirst=True)
