"""
Notification — outbound message sent to a business contact.

Israeli context:
  Primary channels are WhatsApp (360dialog) and Email (SendGrid).
  Notifications are triggered automatically by system events (binder received,
  ready for pickup) or manually by an advisor (payment reminder).

Design decisions:
- content_snapshot stores the rendered message at send time — immutable audit trail.
- retry_count tracks delivery attempts; max retries enforced in service layer.
- is_read / read_at support the notification center UI (bell icon).
- No soft delete — notifications are append-only audit records.
- No updated_at — status transitions are captured via sent_at / failed_at.
"""

from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, SmallInteger
from app.utils.enum_utils import pg_enum

from app.database import Base
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

    id          = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True, index=True)
    client_id   = Column(Integer, ForeignKey("clients.id"),    nullable=True, index=True)
    binder_id   = Column(Integer, ForeignKey("binders.id"),    nullable=True, index=True)

    # ── Message identity ──────────────────────────────────────────────────────
    trigger          = Column(pg_enum(NotificationTrigger),  nullable=False)
    channel          = Column(pg_enum(NotificationChannel),  nullable=False)
    severity         = Column(pg_enum(NotificationSeverity),
                              default=NotificationSeverity.INFO, nullable=False)
    recipient        = Column(String, nullable=False)         # טלפון או כתובת מייל
    content_snapshot = Column(Text,   nullable=False)         # תוכן ההודעה בזמן השליחה

    # ── Delivery status ───────────────────────────────────────────────────────
    status      = Column(pg_enum(NotificationStatus),
                         default=NotificationStatus.PENDING, nullable=False)
    sent_at     = Column(DateTime, nullable=True)
    failed_at   = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(SmallInteger, nullable=False, default=0)  # מספר ניסיונות שליחה

    # ── Read state (notification center) ─────────────────────────────────────
    is_read  = Column(Boolean,  default=False, nullable=False)
    read_at  = Column(DateTime, nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = מערכת
    created_at   = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_notification_business_status", "business_id", "status"),
        Index("idx_notification_client_status",   "client_id",   "status"),
        Index("idx_notification_created_at",      "created_at"),
    )

    def __repr__(self):
        return (
            f"<Notification(id={self.id}, business_id={self.business_id}, "
            f"trigger='{self.trigger}', status='{self.status}')>"
        )