"""reminder: add client_id, make business_id nullable

Revision ID: 0019_reminder_add_client_id_nullable_business
Revises: 0018_status_history_changed_by_nullable
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0019_reminder_add_client_id_nullable_business"
down_revision: str = "0018_status_history_changed_by_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.add_column(sa.Column("client_id", sa.Integer(), nullable=True))
        batch_op.alter_column("business_id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_foreign_key(
            "fk_reminders_client_id", "clients", ["client_id"], ["id"]
        )
        batch_op.create_index("idx_reminder_client_type", ["client_id", "reminder_type"])


def downgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.drop_index("idx_reminder_client_type")
        batch_op.drop_constraint("fk_reminders_client_id", type_="foreignkey")
        batch_op.drop_column("client_id")
        batch_op.alter_column("business_id", existing_type=sa.Integer(), nullable=False)
