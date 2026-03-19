from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, Boolean
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow

# ─── Reminder ─────────────────────────────────────────────────────────────────
 
class ReminderType(str, PyEnum):
    TAX_DEADLINE_APPROACHING = "tax_deadline_approaching"
    BINDER_IDLE = "binder_idle"
    UNPAID_CHARGE = "unpaid_charge"
    CUSTOM = "custom"
 
 
class ReminderStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    CANCELED = "canceled"
 
 
class Reminder(Base):
    __tablename__ = "reminders"
 
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    reminder_type = Column(pg_enum(ReminderType), nullable=False)
    status = Column(pg_enum(ReminderStatus), default=ReminderStatus.PENDING, nullable=False)
    target_date = Column(Date, nullable=False, index=True)
    days_before = Column(Integer, nullable=False)
    send_on = Column(Date, nullable=False, index=True)
    binder_id = Column(Integer, ForeignKey("binders.id"), nullable=True, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=True, index=True)
    tax_deadline_id = Column(Integer, ForeignKey("tax_deadlines.id"), nullable=True, index=True)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
 
    __table_args__ = (
        Index("idx_reminder_status_send_on", "status", "send_on"),
    )
 
    def __repr__(self):
        return f"<Reminder(id={self.id}, business_id={self.business_id}, type='{self.reminder_type}')>"
 