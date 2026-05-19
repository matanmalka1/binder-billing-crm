"""Advance payment model for Israeli tax prepayments.

An ``AdvancePayment`` represents a client tax prepayment (``מקדמה``) for a
given reporting period.

Context:
    Reporting legal entities pay advance payments (``מקדמות``) to the Israeli

    Tax Authority monthly or bi-monthly, based on a configured advance rate.
    based on a percentage of prior-year income.
    The expected amount is derived: turnover_amount × advance_rate / 100 =
    calculated_amount. override_amount replaces the final expected_amount when
    set.

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
    - Uniqueness of (client_record_id, period) is enforced via a partial index
      (WHERE deleted_at IS NULL) — not a hard UniqueConstraint — so that a
      soft-deleted record never blocks recreation of the same period.
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)

from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class AdvancePaymentStatus(str, PyEnum):
    """Lifecycle status of an advance payment."""

    PENDING = "pending"  # Not yet paid
    PAID = "paid"  # Paid in full
    PARTIAL = "partial"  # Paid partially


class PaymentMethod(str, PyEnum):
    """Supported payment methods for an advance payment."""

    BANK_TRANSFER = "bank_transfer"  # Bank transfer
    CREDIT_CARD = "credit_card"  # Credit card
    CHECK = "check"  # Check
    DIRECT_DEBIT = "direct_debit"  # Direct debit — very common for advance payments
    CASH = "cash"  # Cash — rare, exists at post office bank
    OTHER = "other"


class AdvancePayment(Base):
    """SQLAlchemy model for a client's advance tax payment record."""

    __tablename__ = "advance_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_record_id = Column(Integer, ForeignKey("client_records.id"), nullable=False, index=True)

    # ── Period ────────────────────────────────────────────────────────────────
    period = Column(String(7), nullable=False)  # "YYYY-MM" — first month in period
    period_months_count = Column(Integer, nullable=False, default=1)  # 1=monthly, 2=bi-monthly
    due_date = Column(Date, nullable=False)  # Usually the 15th of the month after the period
    due_date_original = Column(Date, nullable=True)
    due_date_effective = Column(Date, nullable=True)
    due_date_override_reason = Column(String(500), nullable=True)

    # ── Amounts ───────────────────────────────────────────────────────────────
    expected_amount = Column(Numeric(10, 2), nullable=True)
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")

    # ── Calculation fields ────────────────────────────────────────────────────
    turnover_amount = Column(Numeric(14, 2), nullable=True)
    advance_rate = Column(Numeric(5, 2), nullable=True)
    calculated_amount = Column(Numeric(12, 2), nullable=True)
    override_amount = Column(Numeric(12, 2), nullable=True)

    # ── Status & payment ──────────────────────────────────────────────────────
    status = Column(
        pg_enum(AdvancePaymentStatus),
        default=AdvancePaymentStatus.PENDING,
        nullable=False,
    )
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(pg_enum(PaymentMethod), nullable=True)

    # ── Cross-domain links ────────────────────────────────────────────────────
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True, index=True)
    tax_calendar_entry_id = Column(
        Integer,
        ForeignKey("tax_calendar_entries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = Column(String(500), nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index(
            "uq_advance_payment_client_record_period_active",
            "client_record_id",
            "period",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index("idx_advance_payment_client_record_period", "client_record_id", "period"),
        Index("idx_advance_payment_status", "status"),
        Index("idx_advance_payment_due_date", "due_date"),
        Index(
            "idx_advance_payment_calendar_entry_active",
            "tax_calendar_entry_id",
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self):
        return (
            f"<AdvancePayment(id={self.id}, client_record_id={self.client_record_id}, "
            f"period='{self.period}', status='{self.status}')>"
        )


from app.advance_payments.models import (
    due_date_snapshot_events,  # noqa: E402,F401  # pylint: disable=unused-import
)
