from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.database import Base
from app.utils.time_utils import utcnow


class AnnualReportDetail(Base):
    """
    Supplementary detail record for an annual report (1:1 with AnnualReport).

    Two distinct write paths — never mix them:

    CACHE columns (credit_points, pension_credit_points, life_insurance_credit_points,
    tuition_credit_points):
        Computed aggregates sourced from AnnualReportCreditPoint rows.
        Written ONLY via AnnualReportDetailRepository.refresh_credit_cache().
        NULL until first computed. Service layer applies statutory defaults when NULL.
        Never set these directly.

    METADATA columns (client_approved_at, internal_notes, amendment_reason,
    pension_contribution, donation_amount, other_credits):
        Real business events written directly by service operations.
        Written ONLY via AnnualReportDetailRepository.update_meta().
    """

    __tablename__ = "annual_report_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=False, unique=True)

    # ── Credit points breakdown (cache — written only by refresh_credit_cache) ──
    # NULL until computed from AnnualReportCreditPoint rows. Service layer falls
    # back to statutory defaults when NULL. Do NOT set these directly.
    credit_points = Column(Numeric(5, 2), nullable=True)
    pension_credit_points = Column(Numeric(5, 2), nullable=True)
    life_insurance_credit_points = Column(Numeric(5, 2), nullable=True)
    tuition_credit_points = Column(Numeric(5, 2), nullable=True)

    # ── Deductions ────────────────────────────────────────────────────────
    pension_contribution = Column(Numeric(12, 2), nullable=True, default=0)
    donation_amount = Column(Numeric(12, 2), nullable=True, default=0)
    other_credits = Column(Numeric(12, 2), nullable=True, default=0)

    # ── Client approval ───────────────────────────────────────────────────
    client_approved_at = Column(DateTime, nullable=True)

    # ── Internal notes ────────────────────────────────────────────────────
    internal_notes = Column(Text,        nullable=True)
    amendment_reason = Column(String(500), nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=True,  onupdate=utcnow)

    def __repr__(self):
        return (
            f"<AnnualReportDetail(id={self.id}, report_id={self.report_id})>"
        )