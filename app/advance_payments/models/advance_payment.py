from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String,
    UniqueConstraint,
)
from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow
# ─── AdvancePayment ───────────────────────────────────────────────────────────
 
class AdvancePaymentStatus(str, PyEnum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
 
 
class AdvancePayment(Base):
    __tablename__ = "advance_payments"
 
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    tax_deadline_id = Column(Integer, ForeignKey("tax_deadlines.id"), nullable=True, index=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    expected_amount = Column(Numeric(10, 2), nullable=True)
    paid_amount = Column(Numeric(10, 2), nullable=True)
    status = Column(pg_enum(AdvancePaymentStatus), default=AdvancePaymentStatus.PENDING, nullable=False)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True, index=True)
    due_date = Column(Date, nullable=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
 
    __table_args__ = (
        UniqueConstraint("business_id", "year", "month", name="uq_advance_payment_business_year_month"),
        Index("idx_advance_payment_business_year", "business_id", "year"),
        Index("idx_advance_payment_status", "status"),
    )
 
    def __repr__(self):
        return f"<AdvancePayment(id={self.id}, business_id={self.business_id}, year={self.year}, month={self.month})>"
 