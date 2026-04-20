"""
Tax Deadline — calendar deadline for tax obligations per client.

Israeli context:
  Covers VAT filing, advance payments (מקדמות), national insurance (ביטוח לאומי),
  and annual report submission deadlines.
  UrgencyLevel is derived in the service layer based on days remaining —
  it is NOT persisted here.

Design decisions:
- No currency column — always ILS per project convention.
- UrgencyLevel enum lives here (used by service layer) but not stored on the model.
- completed_at + completed_by capture who fulfilled the obligation and when.
- period ("YYYY-MM") links the deadline to a reporting period for display
  and reporting; generator deduplication currently uses client + type + due_date.
- advance_payment_id: TaxDeadline knows which AdvancePayment settled it.
  Direction: TaxDeadline → AdvancePayment (not the reverse) to avoid circular FK.
- Soft delete included — TaxDeadline is a client entity.
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
)
from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow


class UrgencyLevel(str, PyEnum):
    """Derived in service layer — not stored in DB."""
    OVERDUE = "overdue"
    RED     = "red"      # ≤ 2 ימים
    YELLOW  = "yellow"   # ≤ 7 ימים
    GREEN   = "green"    # > 7 ימים


class DeadlineType(str, PyEnum):
    VAT                = "vat"
    ADVANCE_PAYMENT    = "advance_payment"
    NATIONAL_INSURANCE = "national_insurance"
    ANNUAL_REPORT      = "annual_report"
    OTHER              = "other"


class TaxDeadlineStatus(str, PyEnum):
    PENDING   = "pending"
    COMPLETED = "completed"
    CANCELED  = "canceled"


class TaxDeadline(Base):
    __tablename__ = "tax_deadlines"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    client_record_id = Column(Integer, ForeignKey("client_records.id"), nullable=False, index=True)

    # ── Deadline identity ─────────────────────────────────────────────────────
    deadline_type = Column(pg_enum(DeadlineType), nullable=False)
    period        = Column(String(7), nullable=True)      # "YYYY-MM" — התקופה שאליה מתייחס המועד
    due_date      = Column(Date, nullable=False, index=True)

    # ── Status ────────────────────────────────────────────────────────────────
    status       = Column(pg_enum(TaxDeadlineStatus),
                          default=TaxDeadlineStatus.PENDING, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ── Settlement link ───────────────────────────────────────────────────────
    advance_payment_id = Column(
        Integer, ForeignKey("advance_payments.id"), nullable=True, index=True
    )  # מי שילם את המועד הזה — רלוונטי ל-deadline_type=ADVANCE_PAYMENT

    # ── Payment info ──────────────────────────────────────────────────────────
    payment_amount = Column(Numeric(10, 2), nullable=True)
    description    = Column(Text, nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        # If advance_payment_id is set, deadline_type must be ADVANCE_PAYMENT.
        # ADVANCE_PAYMENT deadlines may exist without a linked advance_payment_id (auto-generated).
        CheckConstraint(
            "(advance_payment_id IS NULL) OR (deadline_type = 'advance_payment')",
            name="ck_tax_deadline_advance_payment_link",
        ),
        Index("idx_tax_deadline_status",                "status"),
        Index("idx_tax_deadline_type",                  "deadline_type"),
        Index("idx_tax_deadline_client_record_period",  "client_record_id", "period"),
    )

    def __repr__(self):
        return (
            f"<TaxDeadline(id={self.id}, client_record_id={self.client_record_id}, "
            f"type='{self.deadline_type}', due='{self.due_date}')>"
        )
