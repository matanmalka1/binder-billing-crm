from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text

from app.database import Base
from app.utils.time import utcnow


class NotificationChannel(str, PyEnum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class NotificationStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class NotificationTrigger(str, PyEnum):
    BINDER_RECEIVED = "binder_received"
    BINDER_READY_FOR_PICKUP = "binder_ready_for_pickup"
    MANUAL_PAYMENT_REMINDER = "manual_payment_reminder"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    binder_id = Column(Integer, ForeignKey("binders.id"), nullable=True, index=True)
    trigger = Column(Enum(NotificationTrigger), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    recipient = Column(String, nullable=False)
    content_snapshot = Column(Text, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<Notification(id={self.id}, trigger='{self.trigger}', channel='{self.channel}', status='{self.status}')>"
