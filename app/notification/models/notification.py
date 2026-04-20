"""
Notification — outbound message sent to a client or business contact.

Israeli context:
  Primary channels are WhatsApp (360dialog) and Email (SendGrid).
  Notifications are triggered automatically by system events (binder received,
  ready for pickup) or manually by an advisor (payment reminder).

Design decisions:
- client_record_id is the primary anchor (legal entity record).
- business_id is OPTIONAL context — set when the notification is scoped
  to a specific business activity.
- content_snapshot stores the rendered message at send time — immutable audit trail.
- retry_count tracks delivery attempts; max retries enforced in service layer.
- is_read / read_at support the notification center UI (bell icon).
- No soft delete — notifications are append-only audit records.
- No updated_at — status transitions are captured via sent_at / failed_at.
"""

from __future__ import annotations

import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class NotificationChannel(str, PyEnum):
    WHATSAPP = "whatsapp"
    EMAIL    = "email"


class NotificationStatus(str, PyEnum):
    PENDING = "pending"
    SENT    = "sent"
    FAILED  = "failed"


class NotificationTrigger(str, PyEnum):
    BINDER_RECEIVED         = "binder_received"
    BINDER_READY_FOR_PICKUP = "binder_ready_for_pickup"
    MANUAL_PAYMENT_REMINDER = "manual_payment_reminder"


class NotificationSeverity(str, PyEnum):
    INFO     = "info"
    WARNING  = "warning"
    URGENT   = "urgent"
    CRITICAL = "critical"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Anchors ───────────────────────────────────────────────────────────────
    client_record_id: Mapped[int] = mapped_column(
        ForeignKey("client_records.id"), nullable=False, index=True
    )
    # OPTIONAL: set when the notification is scoped to a specific business
    business_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("businesses.id"), nullable=True, index=True
    )
    # OPTIONAL: set when triggered by a binder event
    binder_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("binders.id"), nullable=True, index=True
    )

    # ── Message identity ──────────────────────────────────────────────────────
    trigger: Mapped[NotificationTrigger] = mapped_column(
        pg_enum(NotificationTrigger), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel), nullable=False
    )
    severity: Mapped[NotificationSeverity] = mapped_column(
        pg_enum(NotificationSeverity),
        default=NotificationSeverity.INFO,
        nullable=False,
    )
    recipient:        Mapped[str] = mapped_column(String, nullable=False)  # phone or email
    content_snapshot: Mapped[str] = mapped_column(Text,   nullable=False)  # rendered at send time

    # ── Delivery status ───────────────────────────────────────────────────────
    status: Mapped[NotificationStatus] = mapped_column(
        pg_enum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False,
    )
    sent_at:       Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    failed_at:     Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]]               = mapped_column(Text, nullable=True)
    retry_count:   Mapped[int]                         = mapped_column(
        SmallInteger, nullable=False, default=0
    )

    # ── Read state (notification center) ─────────────────────────────────────
    is_read: Mapped[bool]                         = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime.datetime]]  = mapped_column(nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    triggered_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True  # None = system-triggered
    )
    created_at: Mapped[datetime.datetime] = mapped_column(default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_notification_client_record_status", "client_record_id", "status"),
        Index("idx_notification_business_status",      "business_id", "status"),
        Index("idx_notification_created_at",           "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, client_record_id={self.client_record_id}, "
            f"business_id={self.business_id}, trigger='{self.trigger}', "
            f"status='{self.status}')>"
        )
