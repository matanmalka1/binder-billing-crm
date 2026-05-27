"""notification schema v2: replace trigger enum, drop severity, add columns

Revision ID: 0004_notification_schema_v2
Revises: 0003_vat_due_date_client_index
Create Date: 2026-05-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_notification_schema_v2"
down_revision: Union[str, Sequence[str], None] = "0003_vat_due_date_client_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A. Rename old trigger enum
    op.execute("ALTER TYPE notificationtrigger RENAME TO notificationtrigger_old")

    # B. Create new trigger enum with 13 values
    op.execute(
        """
        CREATE TYPE notificationtrigger AS ENUM (
            'binder_ready_for_handover',
            'binder_missing_documents',
            'binder_general_reminder',
            'invoice_issued',
            'payment_reminder',
            'vat_documents_reminder',
            'annual_report_documents_request',
            'annual_report_client_reminder',
            'signature_request_sent',
            'signature_request_reminder',
            'client_missing_information',
            'client_documents_request',
            'client_general_message'
        )
        """
    )

    # C. Migrate existing rows
    op.execute(
        """
        ALTER TABLE notifications
            ALTER COLUMN trigger TYPE notificationtrigger
            USING (
                CASE trigger::text
                    WHEN 'binder_received'               THEN 'binder_general_reminder'
                    WHEN 'binder_ready_for_handover'     THEN 'binder_ready_for_handover'
                    WHEN 'handover_reminder'             THEN 'binder_general_reminder'
                    WHEN 'annual_report_client_reminder' THEN 'annual_report_client_reminder'
                    WHEN 'manual_payment_reminder'       THEN 'client_general_message'
                    ELSE 'client_general_message'
                END::notificationtrigger
            )
        """
    )

    # D. Drop old enum
    op.execute("DROP TYPE notificationtrigger_old")

    # E. Make recipient nullable (skipped records require recipient=null)
    op.alter_column("notifications", "recipient", nullable=True)

    # F. Drop severity column and type
    op.drop_column("notifications", "severity")
    op.execute("DROP TYPE IF EXISTS notificationseverity")

    # G–L. Add new columns
    op.add_column("notifications", sa.Column("subject_snapshot", sa.Text(), nullable=True))
    op.add_column("notifications", sa.Column("entity_type", sa.String(), nullable=True))
    op.add_column("notifications", sa.Column("entity_id", sa.Integer(), nullable=True))
    op.add_column(
        "notifications",
        sa.Column(
            "signature_request_id",
            sa.Integer(),
            sa.ForeignKey("signature_requests.id"),
            nullable=True,
        ),
    )
    op.add_column("notifications", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.add_column("notifications", sa.Column("request_hash", sa.String(), nullable=True))

    # M–O. Add indexes
    op.create_index("idx_notification_trigger", "notifications", ["trigger"])
    op.create_index("idx_notification_triggered_by", "notifications", ["triggered_by"])
    op.create_index("idx_notification_idempotency", "notifications", ["idempotency_key"])
    op.create_index("idx_notification_signature_request", "notifications", ["signature_request_id"])


def downgrade() -> None:
    op.drop_index("idx_notification_signature_request", table_name="notifications")
    op.drop_index("idx_notification_idempotency", table_name="notifications")
    op.drop_index("idx_notification_triggered_by", table_name="notifications")
    op.drop_index("idx_notification_trigger", table_name="notifications")

    op.drop_column("notifications", "request_hash")
    op.drop_column("notifications", "idempotency_key")
    op.drop_column("notifications", "signature_request_id")
    op.drop_column("notifications", "entity_id")
    op.drop_column("notifications", "entity_type")
    op.drop_column("notifications", "subject_snapshot")

    # Restore severity column and type
    op.execute(
        """
        CREATE TYPE notificationseverity AS ENUM ('info', 'warning', 'urgent', 'critical')
        """
    )
    op.add_column(
        "notifications",
        sa.Column(
            "severity",
            sa.Enum("info", "warning", "urgent", "critical", name="notificationseverity"),
            nullable=False,
            server_default="info",
        ),
    )

    op.alter_column("notifications", "recipient", nullable=False)

    # Restore old trigger enum
    op.execute("ALTER TYPE notificationtrigger RENAME TO notificationtrigger_new")
    op.execute(
        """
        CREATE TYPE notificationtrigger AS ENUM (
            'binder_received',
            'binder_ready_for_handover',
            'handover_reminder',
            'annual_report_client_reminder',
            'manual_payment_reminder'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE notifications
            ALTER COLUMN trigger TYPE notificationtrigger
            USING (
                CASE trigger::text
                    WHEN 'binder_ready_for_handover'     THEN 'binder_ready_for_handover'
                    WHEN 'annual_report_client_reminder' THEN 'annual_report_client_reminder'
                    ELSE 'manual_payment_reminder'
                END::notificationtrigger
            )
        """
    )
    op.execute("DROP TYPE notificationtrigger_new")
