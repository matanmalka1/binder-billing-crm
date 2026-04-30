"""
Reminder — proactive alert scheduled for a future date.

Israeli context:
  Reminders are created automatically by the system (e.g. 7 days before a
  tax deadline) or manually by an advisor. They are dispatched by the daily
  background job when send_on <= today.

Anchor pattern:
  client_record_id is the primary anchor (legal entity record).
  business_id is OPTIONAL context — set when the reminder is scoped to a
  specific business activity. This mirrors the pattern used across all other
  domain models (charges, correspondence, notifications, signature_requests).

Design decisions:
  - send_on is pre-computed (target_date - days_before) for efficient scheduler
    queries — no date arithmetic at dispatch time.
  - One nullable FK per domain entity (binder, charge, tax_deadline,
    annual_report, advance_payment) — only one will be set per reminder
    depending on type. Enforced by service layer, not DB constraint.
  - No notification_id FK — Reminder and Notification are separate concerns;
    the background job creates a Notification when it dispatches a Reminder.
  - Soft delete included — reminders are business entities.
  - canceled_by — records which staff member canceled; null = system.
  - created_by — null = system-generated reminder.
"""

from __future__ import annotations

import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class ReminderType(str, PyEnum):
    TAX_DEADLINE_APPROACHING = "tax_deadline_approaching"
    VAT_FILING               = "vat_filing"
    ADVANCE_PAYMENT_DUE      = "advance_payment_due"
    ANNUAL_REPORT_DEADLINE   = "annual_report_deadline"
    BINDER_IDLE              = "binder_idle"
    UNPAID_CHARGE            = "unpaid_charge"
    DOCUMENT_MISSING         = "document_missing"
    CUSTOM                   = "custom"


class ReminderStatus(str, PyEnum):
    PENDING    = "pending"
    PROCESSING = "processing"  # claimed by background job; in-flight
    SENT       = "sent"
    CANCELED   = "canceled"


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Anchors ───────────────────────────────────────────────────────────────
    client_record_id: Mapped[int] = mapped_column(
        ForeignKey("client_records.id"), nullable=False, index=True
    )
    # OPTIONAL: set when the reminder is scoped to a specific business activity
    business_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("businesses.id"), nullable=True, index=True
    )

    # ── Type & status ─────────────────────────────────────────────────────────
    reminder_type: Mapped[ReminderType] = mapped_column(
        pg_enum(ReminderType), nullable=False
    )
    status: Mapped[ReminderStatus] = mapped_column(
        pg_enum(ReminderStatus), default=ReminderStatus.PENDING, nullable=False
    )

    # ── Scheduling ────────────────────────────────────────────────────────────
    target_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    days_before: Mapped[int]           = mapped_column(Integer, nullable=False)
    send_on:     Mapped[datetime.date] = mapped_column(Date, nullable=False)  # pre-computed: target_date - days_before

    # ── Content ───────────────────────────────────────────────────────────────
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Domain links ──────────────────────────────────────────────────────────
    # At most one should be set, matching the reminder_type.
    # Enforced by service layer — a DB constraint across 5 nullable FKs
    # would be unreadable and fragile.
    binder_id:          Mapped[Optional[int]] = mapped_column(ForeignKey("binders.id"),          nullable=True, index=True)
    charge_id:          Mapped[Optional[int]] = mapped_column(ForeignKey("charges.id"),          nullable=True, index=True)
    tax_deadline_id:    Mapped[Optional[int]] = mapped_column(ForeignKey("tax_deadlines.id"),    nullable=True, index=True)
    annual_report_id:   Mapped[Optional[int]] = mapped_column(ForeignKey("annual_reports.id"),   nullable=True, index=True)
    advance_payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("advance_payments.id"), nullable=True, index=True)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    created_at:  Mapped[datetime.datetime]           = mapped_column(DateTime, default=utcnow, nullable=False)
    sent_at:     Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    canceled_by: Mapped[Optional[int]]               = mapped_column(ForeignKey("users.id"), nullable=True)  # null = system

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)  # null = system-generated

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[Optional[int]]               = mapped_column(ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_reminder_status_send_on",   "status", "send_on"),
        Index("idx_reminder_client_record_type", "client_record_id", "reminder_type"),
        Index("idx_reminder_business_type",      "business_id", "reminder_type"),
        Index(
            "uq_reminder_active",
            "client_record_id",
            "reminder_type",
            "target_date",
            unique=True,
            postgresql_where=(status != ReminderStatus.CANCELED) & deleted_at.is_(None) & tax_deadline_id.is_(None),
            sqlite_where=(status != ReminderStatus.CANCELED) & deleted_at.is_(None) & tax_deadline_id.is_(None),
        ),
        Index(
            "uq_reminder_tax_deadline_active",
            "tax_deadline_id",
            unique=True,
            postgresql_where=(status != ReminderStatus.CANCELED) & deleted_at.is_(None) & tax_deadline_id.is_not(None),
            sqlite_where=(status != ReminderStatus.CANCELED) & deleted_at.is_(None) & tax_deadline_id.is_not(None),
        ),
    )

    def __repr__(self) -> str:
        scope = f"business_id={self.business_id}" if self.business_id else f"client_record_id={self.client_record_id}"
        return (
            f"<Reminder(id={self.id}, {scope}, "
            f"type='{self.reminder_type}', send_on='{self.send_on}')>"
        )
