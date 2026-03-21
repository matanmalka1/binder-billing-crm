# app/charge/models/charge.py
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, Numeric, String, Text, Index,
)
from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow


class ChargeType(str, PyEnum):
    MONTHLY_RETAINER   = "monthly_retainer"    # שוטף חודשי
    ANNUAL_REPORT_FEE  = "annual_report_fee"   # עבור דוח שנתי ספציפי
    VAT_FILING_FEE     = "vat_filing_fee"      # עבודת מע"מ מחוץ לריטיינר
    REPRESENTATION_FEE = "representation_fee"  # ייצוג בדיונים / השגות
    CONSULTATION_FEE   = "consultation_fee"    # ייעוץ חד-פעמי
    OTHER              = "other"


class ChargeStatus(str, PyEnum):
    DRAFT    = "draft"
    ISSUED   = "issued"
    PAID     = "paid"
    CANCELED = "canceled"


class Charge(Base):
    __tablename__ = "charges"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)

    # קישור אופציונלי לדוח שנתי (לאינדיקטור "שולם" ברשימת הדוחות)
    annual_report_id = Column(
        Integer, ForeignKey("annual_reports.id"), nullable=True, index=True
    )

    charge_type = Column(pg_enum(ChargeType), nullable=False)
    status      = Column(
        pg_enum(ChargeStatus), default=ChargeStatus.DRAFT, nullable=False
    )

    amount = Column(Numeric(10, 2), nullable=False)  # תמיד ₪, ללא currency

    # התקופה אליה מתייחס החיוב
    period         = Column(String(7), nullable=True, index=True)  # "YYYY-MM" — החודש הראשון
    months_covered = Column(Integer, default=1, nullable=False)    # כמה חודשים מכוסים

    description = Column(Text, nullable=True)  # טקסט חופשי לשורת החיוב

    # Lifecycle timestamps + actors
    created_at  = Column(DateTime, default=utcnow, nullable=False)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=True)

    issued_at   = Column(DateTime, nullable=True)
    issued_by   = Column(Integer, ForeignKey("users.id"), nullable=True)

    paid_at     = Column(DateTime, nullable=True)
    paid_by     = Column(Integer, ForeignKey("users.id"), nullable=True)

    canceled_at          = Column(DateTime, nullable=True)
    canceled_by          = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancellation_reason  = Column(Text, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_charge_business_period", "business_id", "period"),
        Index("idx_charge_status", "status"),
    )

    def __repr__(self):
        return (
            f"<Charge(id={self.id}, business_id={self.business_id}, "
            f"type='{self.charge_type}', amount={self.amount}, status='{self.status}')>"
        )