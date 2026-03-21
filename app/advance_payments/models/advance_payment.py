"""
Advance Payment — tax prepayment (מקדמה) tracked per business per period.

Israeli context:
  Businesses pay advance payments (מקדמות) to the ITA monthly or bi-monthly,
  calculated as a percentage of prior-year income (advance_rate on BusinessTaxProfile).
  Small/medium businesses typically report bi-monthly; larger ones monthly.

  period follows the same "YYYY-MM" convention as VatWorkItem — the first
  month of the reporting period. period_months_count distinguishes monthly
  (1) from bi-monthly (2) without duplicating the period string logic.

Design decisions:
- period + period_months_count instead of month/year — consistent with VAT,
  supports both frequencies, unique constraint still works.
- paid_at captures the actual payment timestamp for auditing.
- payment_method is an enum — DIRECT_DEBIT is the most common for מקדמות.
- No currency column — always ILS per project convention.
- Soft delete included — AdvancePayment is a business entity.
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String,
    UniqueConstraint,
)
from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow


class AdvancePaymentStatus(str, PyEnum):
    PENDING = "pending"   # טרם שולם
    PAID    = "paid"      # שולם במלואו
    PARTIAL = "partial"   # שולם חלקית
    OVERDUE = "overdue"   # באיחור


class PaymentMethod(str, PyEnum):
    BANK_TRANSFER = "bank_transfer"  # העברה בנקאית
    CREDIT_CARD   = "credit_card"    # כרטיס אשראי
    CHECK         = "check"          # המחאה
    DIRECT_DEBIT  = "direct_debit"   # הוראת קבע — נפוץ מאוד במקדמות
    CASH          = "cash"           # מזומן — נדיר, קיים בבנק הדואר
    OTHER         = "other"


class AdvancePayment(Base):
    __tablename__ = "advance_payments"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)

    # ── Period ────────────────────────────────────────────────────────────────
    period              = Column(String(7), nullable=False)       # "YYYY-MM" — חודש ראשון בתקופה
    period_months_count = Column(Integer, nullable=False, default=1)  # 1=חודשי, 2=דו-חודשי
    due_date            = Column(Date, nullable=False)            # בדרך כלל ה-15 לחודש שאחרי התקופה

    # ── Amounts ───────────────────────────────────────────────────────────────
    expected_amount = Column(Numeric(10, 2), nullable=True)  # לפי שיעור המקדמה
    paid_amount     = Column(Numeric(10, 2), nullable=True)  # בפועל

    # ── Status & payment ──────────────────────────────────────────────────────
    status         = Column(pg_enum(AdvancePaymentStatus),
                            default=AdvancePaymentStatus.PENDING, nullable=False)
    paid_at        = Column(DateTime, nullable=True)              # מתי שולם בפועל
    payment_method = Column(pg_enum(PaymentMethod), nullable=True)  # אמצעי תשלום

    # ── Cross-domain links ────────────────────────────────────────────────────
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True, index=True)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = Column(String(500), nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "business_id", "period",
            name="uq_advance_payment_business_period",
        ),
        Index("idx_advance_payment_business_period", "business_id", "period"),
        Index("idx_advance_payment_status",          "status"),
        Index("idx_advance_payment_due_date",        "due_date"),
    )

    def __repr__(self):
        return (
            f"<AdvancePayment(id={self.id}, business_id={self.business_id}, "
            f"period='{self.period}', status='{self.status}')>"
        )