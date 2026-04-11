"""reminder: backfill client_id for client-scoped reminder types

Revision ID: 0020_backfill_reminder_client_id
Revises: 5c91bc1c0828
Create Date: 2026-04-11

For TAX_DEADLINE_APPROACHING, VAT_FILING, ANNUAL_REPORT_DEADLINE, and BINDER_IDLE
reminders created before 0019, business_id was set to an arbitrary first business.
This migration reads the client_id from the linked entity and writes it directly,
then nulls business_id on those rows.
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0020_backfill_reminder_client_id"
down_revision: str = "5c91bc1c0828"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # TAX_DEADLINE_APPROACHING — client_id from tax_deadlines.client_id
    conn.execute(sa.text("""
        UPDATE reminders
        SET client_id = (
            SELECT td.client_id
            FROM tax_deadlines td
            WHERE td.id = reminders.tax_deadline_id
        ),
        business_id = NULL
        WHERE reminder_type = 'tax_deadline_approaching'
          AND tax_deadline_id IS NOT NULL
          AND client_id IS NULL
    """))

    # VAT_FILING — client_id from tax_deadlines.client_id
    conn.execute(sa.text("""
        UPDATE reminders
        SET client_id = (
            SELECT td.client_id
            FROM tax_deadlines td
            WHERE td.id = reminders.tax_deadline_id
        ),
        business_id = NULL
        WHERE reminder_type = 'vat_filing'
          AND tax_deadline_id IS NOT NULL
          AND client_id IS NULL
    """))

    # ANNUAL_REPORT_DEADLINE — client_id from annual_reports.client_id
    conn.execute(sa.text("""
        UPDATE reminders
        SET client_id = (
            SELECT ar.client_id
            FROM annual_reports ar
            WHERE ar.id = reminders.annual_report_id
        ),
        business_id = NULL
        WHERE reminder_type = 'annual_report_deadline'
          AND annual_report_id IS NOT NULL
          AND client_id IS NULL
    """))

    # BINDER_IDLE — client_id from binders.client_id
    conn.execute(sa.text("""
        UPDATE reminders
        SET client_id = (
            SELECT b.client_id
            FROM binders b
            WHERE b.id = reminders.binder_id
        ),
        business_id = NULL
        WHERE reminder_type = 'binder_idle'
          AND binder_id IS NOT NULL
          AND client_id IS NULL
    """))

    # VAT_FILING reminders created by the compliance job have no tax_deadline_id —
    # they have no linked entity other than the business. Resolve via business→client.
    conn.execute(sa.text("""
        UPDATE reminders
        SET client_id = (
            SELECT b.client_id
            FROM businesses b
            WHERE b.id = reminders.business_id
        ),
        business_id = NULL
        WHERE reminder_type = 'vat_filing'
          AND tax_deadline_id IS NULL
          AND client_id IS NULL
          AND business_id IS NOT NULL
    """))


def downgrade() -> None:
    # Cannot safely reverse: original business_id is gone. No-op.
    pass
