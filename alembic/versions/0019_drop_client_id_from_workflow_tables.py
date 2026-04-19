"""drop_client_id_from_workflow_tables

Revision ID: 0019_drop_client_id_from_workflow_tables
Revises: 0018_make_client_record_id_not_null
Create Date: 2026-04-19

Run:
- Upgrade:   APP_ENV=development ENV_FILE=.env.development python3 -m alembic upgrade 0019_drop_client_id_from_workflow_tables
- Downgrade: APP_ENV=development ENV_FILE=.env.development python3 -m alembic downgrade 0018_make_client_record_id_not_null

Notes:
- Drops legacy client_id column from all 13 workflow tables.
- client_record_id (NOT NULL) is now the sole identity anchor.
- Does NOT drop: clients.id (PK), businesses.client_id (permanent ownership FK).
- Tables: annual_reports, vat_work_items, tax_deadlines, binders, advance_payments,
  reminders, charges, notifications, correspondence_entries, signature_requests,
  authority_contacts, binder_handovers, permanent_documents.
- Downgrade re-adds the columns as nullable integers (no FK, no data restoration).
"""

from alembic import op
import sqlalchemy as sa

revision = "0019_drop_client_id_from_workflow_tables"
down_revision = "0018_make_client_record_id_not_null"
branch_labels = None
depends_on = None

_TABLES = [
    "annual_reports",
    "vat_work_items",
    "tax_deadlines",
    "binders",
    "advance_payments",
    "reminders",
    "charges",
    "notifications",
    "correspondence_entries",
    "signature_requests",
    "authority_contacts",
    "binder_handovers",
    "permanent_documents",
]


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    for table in _TABLES:
        if dialect == "sqlite":
            with op.batch_alter_table(table, recreate="auto") as batch_op:
                batch_op.drop_column("client_id")
        else:
            op.drop_column(table, "client_id")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    for table in _TABLES:
        if dialect == "sqlite":
            with op.batch_alter_table(table, recreate="auto") as batch_op:
                batch_op.add_column(sa.Column("client_id", sa.Integer(), nullable=True))
        else:
            op.add_column(table, sa.Column("client_id", sa.Integer(), nullable=True))
