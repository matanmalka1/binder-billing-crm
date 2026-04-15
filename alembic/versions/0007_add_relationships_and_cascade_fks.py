"""add_relationships_and_cascade_fks

Revision ID: a61d76155e04
Revises: 0006_fix_annual_report_line_integrity
Create Date: 2026-04-15 10:16:17.665478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a61d76155e04'
down_revision: Union[str, Sequence[str], None] = '0006_fix_annual_report_line_integrity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables and their FK columns that need ON DELETE CASCADE added.
# Each entry: (table, fk_col, ref_table, ref_col)
_CASCADE_FKS = [
    ('annual_report_credit_points', 'annual_report_id', 'annual_reports', 'id'),
    ('annual_report_details', 'report_id', 'annual_reports', 'id'),
    ('annual_report_expense_lines', 'annual_report_id', 'annual_reports', 'id'),
    ('annual_report_income_lines', 'annual_report_id', 'annual_reports', 'id'),
    ('annual_report_schedules', 'annual_report_id', 'annual_reports', 'id'),
    ('binder_intakes', 'binder_id', 'binders', 'id'),
    ('vat_invoices', 'work_item_id', 'vat_work_items', 'id'),
]


def upgrade() -> None:
    """Add ON DELETE CASCADE to FK constraints. Uses batch/recreate for SQLite compat."""
    for table, fk_col, ref_table, ref_col in _CASCADE_FKS:
        with op.batch_alter_table(table, recreate='always') as batch_op:
            batch_op.create_foreign_key(
                f'fk_{table}_{fk_col}_cascade',
                ref_table, [fk_col], [ref_col], ondelete='CASCADE',
            )


def downgrade() -> None:
    """Remove named CASCADE FK constraints and replace with plain FKs."""
    for table, fk_col, ref_table, ref_col in reversed(_CASCADE_FKS):
        with op.batch_alter_table(table, recreate='always') as batch_op:
            batch_op.drop_constraint(f'fk_{table}_{fk_col}_cascade', type_='foreignkey')
            batch_op.create_foreign_key(
                None, ref_table, [fk_col], [ref_col],
            )
