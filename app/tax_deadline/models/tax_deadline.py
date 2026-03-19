# ─── TaxDeadline ──────────────────────────────────────────────────────────────

from enum import Enum as PyEnum

from sqlalchemy import (Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text)

from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow

 
class DeadlineType(str, PyEnum):
    VAT = "vat"
    ADVANCE_PAYMENT = "advance_payment"
    NATIONAL_INSURANCE = "national_insurance"
    ANNUAL_REPORT = "annual_report"
    OTHER = "other"
 
 
class TaxDeadlineStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
 
 
class TaxDeadline(Base):
    __tablename__ = "tax_deadlines"
 
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    deadline_type = Column(pg_enum(DeadlineType), nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(pg_enum(TaxDeadlineStatus), default=TaxDeadlineStatus.PENDING, nullable=False)
    payment_amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="ILS", nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
 
    __table_args__ = (
        Index("idx_tax_deadline_status", "status"),
        Index("idx_tax_deadline_type", "deadline_type"),
    )
 
    def __repr__(self):
        return f"<TaxDeadline(id={self.id}, business_id={self.business_id}, type='{self.deadline_type}')>"