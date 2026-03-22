from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.database import Base
from app.utils.time_utils import utcnow


class AnnualReportDetail(Base):
    __tablename__ = "annual_report_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=False, unique=True)

    # ── Credit points breakdown ────────────────────────────────────────────
    credit_points = Column(Numeric(5, 2), nullable=True, default=2.25)
    pension_credit_points = Column(Numeric(5, 2), nullable=True, default=0)
    life_insurance_credit_points = Column(Numeric(5, 2), nullable=True, default=0)
    tuition_credit_points = Column(Numeric(5, 2), nullable=True, default=0)

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
