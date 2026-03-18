"""Income line items for an annual tax report."""

from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class IncomeSourceType(str, PyEnum):
    BUSINESS = "business"           # הכנסות עסק / עצמאי
    SALARY = "salary"               # משכורת / שכר עבודה
    INTEREST = "interest"           # ריבית
    DIVIDENDS = "dividends"         # דיבידנד
    CAPITAL_GAINS = "capital_gains" # רווחי הון
    RENTAL = "rental"               # שכירות
    FOREIGN = "foreign"             # הכנסות מחו"ל
    PENSION = "pension"             # פנסיה / קצבה
    OTHER = "other"                 # אחר


class AnnualReportIncomeLine(Base):
    """
    Single income line attached to an annual report.

    One report may have multiple income lines of different source types.
    """

    __tablename__ = "annual_report_income_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annual_report_id = Column(
        Integer, ForeignKey("annual_reports.id"), nullable=False, index=True
    )
    source_type = Column(pg_enum(IncomeSourceType), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    def __repr__(self):
        return (
            f"<AnnualReportIncomeLine(id={self.id}, report_id={self.annual_report_id}, "
            f"type={self.source_type}, amount={self.amount})>"
        )


__all__ = ["AnnualReportIncomeLine", "IncomeSourceType"]
