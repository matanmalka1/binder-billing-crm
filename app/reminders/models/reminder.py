from __future__ import annotations

import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class ReminderType(str, PyEnum):
    BINDER_IDLE      = "binder_idle"
    DOCUMENT_MISSING = "document_missing"
    CUSTOM           = "custom"


class ReminderStatus(str, PyEnum):
    PENDING  = "pending"
    SENT     = "sent"
    CANCELED = "canceled"


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_record_id: Mapped[int] = mapped_column(ForeignKey("client_records.id"), nullable=False, index=True)
    business_id: Mapped[Optional[int]] = mapped_column(ForeignKey("businesses.id"), nullable=True, index=True)

    reminder_type: Mapped[ReminderType] = mapped_column(pg_enum(ReminderType), nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(pg_enum(ReminderStatus), default=ReminderStatus.PENDING, nullable=False)

    target_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    days_before: Mapped[int] = mapped_column(Integer, nullable=False)
    send_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    binder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("binders.id"), nullable=True, index=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    canceled_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_reminder_client_record_type", "client_record_id", "reminder_type"),
        Index("idx_reminder_business_type", "business_id", "reminder_type"),
        Index(
            "uq_reminder_active",
            "client_record_id",
            "reminder_type",
            "target_date",
            unique=True,
            postgresql_where=(status != ReminderStatus.CANCELED) & deleted_at.is_(None),
            sqlite_where=(status != ReminderStatus.CANCELED) & deleted_at.is_(None),
        ),
    )

    def __repr__(self) -> str:
        scope = f"business_id={self.business_id}" if self.business_id else f"client_record_id={self.client_record_id}"
        return f"<Reminder(id={self.id}, {scope}, type='{self.reminder_type}', send_on='{self.send_on}')>"
