from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow

# ─── Notification ─────────────────────────────────────────────────────────────
 
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
 
 
class NotificationSeverity(str, PyEnum):
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"
 
 
class Notification(Base):
    __tablename__ = "notifications"
 
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    binder_id = Column(Integer, ForeignKey("binders.id"), nullable=True, index=True)
    trigger = Column(pg_enum(NotificationTrigger), nullable=False)
    channel = Column(pg_enum(NotificationChannel), nullable=False)
    status = Column(pg_enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    severity = Column(pg_enum(NotificationSeverity), default=NotificationSeverity.INFO, nullable=False)
    recipient = Column(String, nullable=False)
    content_snapshot = Column(Text, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True)
 
    def __repr__(self):
        return f"<Notification(id={self.id}, business_id={self.business_id}, trigger='{self.trigger}')>"
 