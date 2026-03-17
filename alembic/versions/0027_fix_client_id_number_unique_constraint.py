"""fix client id_number unique constraint to allow soft-deleted duplicates

Revision ID: 0027_fix_client_id_number_unique_constraint
Revises: 0026_fix_vat_invoice_enum_case
Create Date: 2026-03-17

The global unique constraint on clients.id_number prevents re-creating a client
whose record was soft-deleted (deleted_at IS NOT NULL). The fix:
  1. Drop the global unique constraint/index
  2. Add a partial unique index covering only active rows (deleted_at IS NULL)

SQLite does not support partial indexes — the partial index is PostgreSQL-only.
In SQLite (dev) we fall back to a plain non-unique index so tests still pass.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0027_fix_client_id_number_unique_constraint"
down_revision = "0026_fix_vat_invoice_enum_case"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: recreate table without the unique constraint
        # (SQLite does not support DROP CONSTRAINT)
        with op.batch_alter_table("clients") as batch_op:
            batch_op.drop_index("ix_clients_id_number")
        with op.batch_alter_table("clients") as batch_op:
            batch_op.create_index("ix_clients_id_number", ["id_number"])
    else:
        # PostgreSQL: drop global unique index, add partial unique index
        op.drop_index("ix_clients_id_number", table_name="clients")
        op.execute(
            """
            CREATE UNIQUE INDEX ix_clients_id_number_active
            ON clients (id_number)
            WHERE deleted_at IS NULL
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("clients") as batch_op:
            batch_op.drop_index("ix_clients_id_number")
        with op.batch_alter_table("clients") as batch_op:
            batch_op.create_index("ix_clients_id_number", ["id_number"], unique=True)
    else:
        op.execute("DROP INDEX IF EXISTS ix_clients_id_number_active")
        op.create_index("ix_clients_id_number", "clients", ["id_number"], unique=True)
