"""Redefine reminders as scheduler triggers.

Revision ID: 0003_scheduler_reminders
Revises: 0002_require_tax_calendar_links
Create Date: 2026-05-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_scheduler_reminders"
down_revision = "0002_require_tax_calendar_links"
branch_labels = None
depends_on = None

_status = sa.Enum(
    "scheduled", "fired", "canceled", "failed", name="reminderstatus"
)
_action = sa.Enum(
    "CREATE_TASK",
    "SEND_NOTIFICATION",
    "CREATE_TASK_AND_NOTIFY",
    name="reminderactiontype",
)


def upgrade() -> None:
    op.drop_table("reminders")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="remindertype").drop(bind, checkfirst=True)
        sa.Enum(name="reminderstatus").drop(bind, checkfirst=True)
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fire_at", sa.DateTime(), nullable=False),
        sa.Column("status", _status, nullable=False),
        sa.Column("action_type", _action, nullable=False),
        sa.Column("source_domain", sa.String(length=100), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("target_task_id", sa.Integer(), nullable=True),
        sa.Column("notification_template_key", sa.String(length=100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("fired_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reminders_fire_at"), "reminders", ["fire_at"])
    op.create_index(op.f("ix_reminders_status"), "reminders", ["status"])
    op.create_index("idx_reminders_status_fire_at", "reminders", ["status", "fire_at"])


def downgrade() -> None:
    op.drop_index("idx_reminders_status_fire_at", table_name="reminders")
    op.drop_index(op.f("ix_reminders_status"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_fire_at"), table_name="reminders")
    op.drop_table("reminders")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="reminderactiontype").drop(bind, checkfirst=True)
        sa.Enum(name="reminderstatus").drop(bind, checkfirst=True)
    old_type = sa.Enum("binder_idle", "document_missing", "custom", name="remindertype")
    old_status = sa.Enum("pending", "sent", "canceled", name="reminderstatus")
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_record_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=True),
        sa.Column("reminder_type", old_type, nullable=False),
        sa.Column("status", old_status, nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("days_before", sa.Integer(), nullable=False),
        sa.Column("send_on", sa.Date(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("binder_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("canceled_by", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
