from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String

from app.database import Base


class ChargeType(str, PyEnum):
    RETAINER = "retainer"
    ONE_TIME = "one_time"


class ChargeStatus(str, PyEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELED = "canceled"


class Charge(Base):
    __tablename__ = "charges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="ILS", nullable=False)
    charge_type = Column(Enum(ChargeType), nullable=False)
    period = Column(String(7), nullable=True)  # YYYY-MM format
    status = Column(Enum(ChargeStatus), default=ChargeStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    issued_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Charge(id={self.id}, client_id={self.client_id}, amount={self.amount}, status='{self.status}')>"