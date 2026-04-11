"""notification: add client_id, make business_id nullable

Revision ID: 0021_notification_add_client_id
Revises: 0020_backfill_reminder_client_id
Create Date: 2026-04-11

Client-scoped obligations (tax deadlines, VAT) now send notifications directly
to the client, not through an arbitrary business. This adds client_id (nullable)
and relaxes business_id to nullable so client-owned notification rows can be
persisted without a business FK.
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0021_notification_add_client_id"
down_revision: str = "0020_backfill_reminder_client_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("client_id", sa.Integer(), nullable=True))
        batch_op.alter_column("business_id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_foreign_key(
            "fk_notifications_client_id", "clients", ["client_id"], ["id"]
        )
        batch_op.create_index("idx_notification_client_status", ["client_id", "status"])


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_index("idx_notification_client_status")
        batch_op.drop_constraint("fk_notifications_client_id", type_="foreignkey")
        batch_op.drop_column("client_id")
        batch_op.alter_column("business_id", existing_type=sa.Integer(), nullable=False)
