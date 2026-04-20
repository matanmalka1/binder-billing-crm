"""add_terminal_closure_states

Revision ID: 0021_add_terminal_closure_states
Revises: 0020_add_domain_identity_unique_constraints
Create Date: 2026-04-20

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0021_add_terminal_closure_states
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0020_add_domain_identity_unique_constraints

Notes:
- Adds new terminal enum values for VAT work items, annual reports, and binders.
- PostgreSQL enums are altered in-place; SQLite has no enum DDL to run here.
- Downgrade is intentionally a no-op because PostgreSQL enum values cannot be removed safely.
"""

from alembic import op
import sqlalchemy as sa

revision = "0021_add_terminal_closure_states"
down_revision = "0020_add_domain_identity_unique_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("ALTER TYPE vatworkitemstatus ADD VALUE IF NOT EXISTS 'canceled'"))
    op.execute(sa.text("ALTER TYPE vatworkitemstatus ADD VALUE IF NOT EXISTS 'archived'"))
    op.execute(sa.text("ALTER TYPE annualreportstatus ADD VALUE IF NOT EXISTS 'canceled'"))
    op.execute(sa.text("ALTER TYPE binderstatus ADD VALUE IF NOT EXISTS 'archived_in_office'"))


def downgrade() -> None:
    pass
