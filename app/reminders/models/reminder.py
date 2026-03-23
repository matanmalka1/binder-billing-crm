"""
Reminder — proactive alert scheduled for a future date.

Israeli context:
  Reminders are created automatically by the system (e.g. 7 days before a
  tax deadline) or manually by an advisor. They are dispatched by the daily
  background job when send_on <= today.

Design decisions:
- send_on is pre-computed (target_date - days_before) for efficient scheduler
  queries — no date arithmetic at dispatch time.
- One nullable FK per domain entity (binder, charge, tax_deadline,
  annual_report) — only one will be set per reminder depending on type.
- No notification_id FK — Reminder and Notification are separate concerns;
  the background job creates a Notification when it dispatches a Reminder.
- Soft delete included — reminders are business entities.
- canceled_by added — useful to know which staff member canceled.
"""

from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class ReminderType(str, PyEnum):
    TAX_DEADLINE_APPROACHING = "tax_deadline_approaching"  # מועד מס כללי מתקרב
    VAT_FILING               = "vat_filing"                # מועד דוח מע"מ
    ADVANCE_PAYMENT_DUE      = "advance_payment_due"       # תשלום מקדמה
    ANNUAL_REPORT_DEADLINE   = "annual_report_deadline"    # מועד הגשת דוח שנתי
    BINDER_IDLE              = "binder_idle"               # תיק לא פעיל
    UNPAID_CHARGE            = "unpaid_charge"             # חיוב שלא שולם
    DOCUMENT_MISSING         = "document_missing"          # מסמך חסר מהלקוח
    CUSTOM                   = "custom"                    # תזכורת ידנית


class ReminderStatus(str, PyEnum):
    PENDING    = "pending"
    PROCESSING = "processing"  # claimed by background job; in-flight
    SENT       = "sent"
    CANCELED   = "canceled"


class Reminder(Base):
    __tablename__ = "reminders"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)

    # ── Type & status ─────────────────────────────────────────────────────────
    reminder_type = Column(pg_enum(ReminderType),   nullable=False)
    status        = Column(pg_enum(ReminderStatus),
                           default=ReminderStatus.PENDING, nullable=False)

    # ── Scheduling ────────────────────────────────────────────────────────────
    target_date = Column(Date, nullable=False)         # תאריך האירוע עצמו
    days_before = Column(Integer, nullable=False)      # כמה ימים לפני לשלוח
    send_on     = Column(Date, nullable=False, index=True)  # pre-computed: target_date - days_before

    # ── Content ───────────────────────────────────────────────────────────────
    message = Column(Text, nullable=False)

    # ── Domain links (one set per reminder type) ──────────────────────────────
    binder_id          = Column(Integer, ForeignKey("binders.id"),          nullable=True, index=True)
    charge_id          = Column(Integer, ForeignKey("charges.id"),          nullable=True, index=True)
    tax_deadline_id    = Column(Integer, ForeignKey("tax_deadlines.id"),    nullable=True, index=True)
    annual_report_id   = Column(Integer, ForeignKey("annual_reports.id"),   nullable=True, index=True)
    advance_payment_id = Column(Integer, ForeignKey("advance_payments.id"), nullable=True, index=True)

    # ── Lifecycle timestamps ──────────────────────────────────────────────────
    created_at   = Column(DateTime, default=utcnow, nullable=False)
    sent_at      = Column(DateTime, nullable=True)
    canceled_at  = Column(DateTime, nullable=True)
    canceled_by  = Column(Integer, ForeignKey("users.id"), nullable=True)  # מי ביטל

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = מערכת

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_reminder_status_send_on", "status", "send_on"),
        Index("idx_reminder_business_type",  "business_id", "reminder_type"),
    )

    def __repr__(self):
        return (
            f"<Reminder(id={self.id}, business_id={self.business_id}, "
            f"type='{self.reminder_type}', send_on='{self.send_on}')>"
        )