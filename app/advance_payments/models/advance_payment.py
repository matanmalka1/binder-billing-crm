from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric,
    UniqueConstraint,
)

from app.database import Base
from app.utils.time import utcnow


class AdvancePaymentStatus(str, PyEnum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"


class AdvancePayment(Base):
    __tablename__ = "advance_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    tax_deadline_id = Column(
        Integer, ForeignKey("tax_deadlines.id"), nullable=True, index=True
    )
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    expected_amount = Column(Numeric(10, 2), nullable=True)
    paid_amount = Column(Numeric(10, 2), nullable=True)
    status = Column(
        Enum(AdvancePaymentStatus),
        default=AdvancePaymentStatus.PENDING,
        nullable=False,
    )
    due_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", name="uq_advance_payment_client_year_month"),
        Index("idx_advance_payment_client_year", "client_id", "year"),
        Index("idx_advance_payment_status", "status"),
    )

    def __repr__(self):
        return (
            f"<AdvancePayment(id={self.id}, client_id={self.client_id}, "
            f"year={self.year}, month={self.month}, status='{self.status}')>"
        )
