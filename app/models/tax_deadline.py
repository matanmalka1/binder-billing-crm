from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Index

from app.database import Base
from app.utils.time import utcnow


class DeadlineType(str, PyEnum):
    VAT = "vat"
    ADVANCE_PAYMENT = "advance_payment"
    NATIONAL_INSURANCE = "national_insurance"
    ANNUAL_REPORT = "annual_report"
    OTHER = "other"


class UrgencyLevel(str, PyEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    OVERDUE = "overdue"


class TaxDeadline(Base):
    __tablename__ = "tax_deadlines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    deadline_type = Column(Enum(DeadlineType), nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String, default="pending", nullable=False)

    # Financial
    payment_amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="ILS", nullable=False)

    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_tax_deadline_status", "status"),
        Index("idx_tax_deadline_type", "deadline_type"),
    )

    def __repr__(self):
        return (
            f"<TaxDeadline(id={self.id}, client_id={self.client_id}, "
            f"type='{self.deadline_type}', due_date={self.due_date})>"
        )