from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, Boolean

from app.database import Base
from app.utils.time import utcnow


class ReminderType(str, PyEnum):
    """Types of reminders."""
    TAX_DEADLINE_APPROACHING = "tax_deadline_approaching"
    BINDER_IDLE = "binder_idle"
    UNPAID_CHARGE = "unpaid_charge"
    CUSTOM = "custom"


class ReminderStatus(str, PyEnum):
    """Reminder status."""
    PENDING = "pending"
    SENT = "sent"
    CANCELED = "canceled"


class Reminder(Base):
    """
    Proactive reminder system.
    
    Stores scheduled reminders that trigger notifications
    X days before an event.
    """
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    reminder_type = Column(Enum(ReminderType), nullable=False)
    status = Column(Enum(ReminderStatus), default=ReminderStatus.PENDING, nullable=False)
    
    # Target date (when the actual event occurs)
    target_date = Column(Date, nullable=False, index=True)
    
    # Days before target to send reminder
    days_before = Column(Integer, nullable=False)
    
    # When to actually send (calculated: target_date - days_before)
    send_on = Column(Date, nullable=False, index=True)
    
    # Reference to related entity
    binder_id = Column(Integer, ForeignKey("binders.id"), nullable=True, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=True, index=True)
    tax_deadline_id = Column(Integer, ForeignKey("tax_deadlines.id"), nullable=True, index=True)
    
    # Message
    message = Column(Text, nullable=False)
    
    # Tracking
    created_at = Column(DateTime, default=utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("idx_reminder_status_send_on", "status", "send_on"),
    )

    def __repr__(self):
        return f"<Reminder(id={self.id}, type='{self.reminder_type}', status='{self.status}')>"
