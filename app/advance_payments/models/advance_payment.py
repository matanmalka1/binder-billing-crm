"""Advance payment model for Israeli tax prepayments.

An ``AdvancePayment`` represents a client tax prepayment (``מקדמה``) for a
given reporting period.

Context:
    Businesses pay advance payments (``מקדמות``) to the Israeli Tax Authority
    monthly or bi-monthly, based on a percentage of prior-year income
    (``advance_rate`` on ``Client``). Small and medium businesses typically
    report bi-monthly, while larger businesses usually report monthly.

Period handling:
    ``period`` follows the same ``YYYY-MM`` convention as ``VatWorkItem`` and
    stores the first month of the reporting period. ``period_months_count``
    distinguishes monthly (1) from bi-monthly (2) periods without duplicating
    period logic.

Design notes:
    - ``period`` and ``period_months_count`` are used instead of separate month
      and year fields for consistency with VAT handling.
    - ``paid_at`` stores the actual payment timestamp for auditability.
    - ``payment_method`` is an enum; direct debit is the most common option for
      advance payments.
    - Currency is always ILS by project convention, so no currency column is
      stored.
    - Soft deletion is enabled because this is a client-owned entity.
    - Uniqueness of (client_id, period) is enforced via a partial index
      (WHERE deleted_at IS NULL) — not a hard UniqueConstraint — so that a
      soft-deleted record never blocks recreation of the same period.
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, text,
)
from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow


class AdvancePaymentStatus(str, PyEnum):
    """Lifecycle status of an advance payment."""

    PENDING = "pending"   # Not yet paid
    PAID    = "paid"      # Paid in full
    PARTIAL = "partial"   # Paid partially
    OVERDUE = "overdue"   # Overdue


class PaymentMethod(str, PyEnum):
    """Supported payment methods for an advance payment."""

    BANK_TRANSFER = "bank_transfer"  # Bank transfer
    CREDIT_CARD   = "credit_card"    # Credit card
    CHECK         = "check"          # Check
    DIRECT_DEBIT  = "direct_debit"   # Direct debit — very common for advance payments
    CASH          = "cash"           # Cash — rare, exists at post office bank
    OTHER         = "other"


class AdvancePayment(Base):
    """SQLAlchemy model for a client's advance tax payment record."""

    __tablename__ = "advance_payments"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    client_record_id = Column(Integer, ForeignKey("client_records.id"), nullable=True, index=True)

    # ── Period ────────────────────────────────────────────────────────────────
    period              = Column(String(7), nullable=False)       # "YYYY-MM" — first month in period
    period_months_count = Column(Integer, nullable=False, default=1)  # 1=monthly, 2=bi-monthly
    due_date            = Column(Date, nullable=False)            # Usually the 15th of the month after the period

    # ── Amounts ───────────────────────────────────────────────────────────────
    expected_amount = Column(Numeric(10, 2), nullable=True)  # According to advance rate
    paid_amount     = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")

    # ── Status & payment ──────────────────────────────────────────────────────
    status         = Column(pg_enum(AdvancePaymentStatus),
                            default=AdvancePaymentStatus.PENDING, nullable=False)
    paid_at        = Column(DateTime, nullable=True)
    payment_method = Column(pg_enum(PaymentMethod), nullable=True)

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
        # Partial unique: a soft-deleted row never blocks a new record for the
        # same (client_id, period). Mirrors the pattern used in vat_work_items.
        Index(
            "uq_advance_payment_client_period_active",
            "client_id", "period",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index("idx_advance_payment_client_period", "client_id", "period"),
        Index("idx_advance_payment_status",        "status"),
        Index("idx_advance_payment_due_date",      "due_date"),
    )

    def __repr__(self):
        return (
            f"<AdvancePayment(id={self.id}, client_id={self.client_id}, "
            f"period='{self.period}', status='{self.status}')>"
        )