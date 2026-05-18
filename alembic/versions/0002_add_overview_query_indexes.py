"""add overview query indexes

Revision ID: 0002_add_overview_query_indexes
Revises: 0001_initial
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_add_overview_query_indexes"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    op.create_index("idx_notification_status", "notifications", ["status"])
    op.create_index(
        "idx_sig_request_pending_sent_active",
        "signature_requests",
        ["status", "sent_at"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )
    op.create_index(
        "idx_annual_report_tax_year_status_active",
        "annual_reports",
        ["tax_year", "status"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )
    op.create_index(
        "idx_annual_report_calendar_entry_active",
        "annual_reports",
        ["tax_calendar_entry_id"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )
    op.create_index(
        "idx_vat_work_items_calendar_entry_active",
        "vat_work_items",
        ["tax_calendar_entry_id"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )
    op.create_index(
        "idx_advance_payment_calendar_entry_active",
        "advance_payments",
        ["tax_calendar_entry_id"],
        postgresql_where=ACTIVE,
        sqlite_where=ACTIVE,
    )
    op.create_index(
        "idx_tax_calendar_entries_year_obligation",
        "tax_calendar_entries",
        ["tax_year", "obligation_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_tax_calendar_entries_year_obligation",
        table_name="tax_calendar_entries",
    )
    op.drop_index(
        "idx_advance_payment_calendar_entry_active",
        table_name="advance_payments",
    )
    op.drop_index(
        "idx_vat_work_items_calendar_entry_active",
        table_name="vat_work_items",
    )
    op.drop_index(
        "idx_annual_report_calendar_entry_active",
        table_name="annual_reports",
    )
    op.drop_index(
        "idx_annual_report_tax_year_status_active",
        table_name="annual_reports",
    )
    op.drop_index(
        "idx_sig_request_pending_sent_active",
        table_name="signature_requests",
    )
    op.drop_index("idx_notification_status", table_name="notifications")
