"""Deductible expense line items for an annual tax report."""

from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow

class ExpenseCategoryType(str, PyEnum):
    OFFICE_RENT = "office_rent"               # שכירות משרד
    PROFESSIONAL_SERVICES = "professional_services"  # שירותים מקצועיים
    SALARIES = "salaries"                     # שכר עבודה
    DEPRECIATION = "depreciation"             # פחת
    VEHICLE = "vehicle"                       # רכב
    MARKETING = "marketing"                   # שיווק ופרסום
    INSURANCE = "insurance"                   # ביטוח
    COMMUNICATION = "communication"           # תקשורת
    TRAVEL = "travel"                         # נסיעות
    TRAINING = "training"                     # הכשרה מקצועית
    BANK_FEES = "bank_fees"                   # עמלות בנק
    OTHER = "other"                           # אחר


class AnnualReportExpenseLine(Base):
    """
    Single deductible expense line attached to an annual report.
    """

    __tablename__ = "annual_report_expense_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annual_report_id = Column(
        Integer, ForeignKey("annual_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = Column(pg_enum(ExpenseCategoryType), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    recognition_rate = Column(Numeric(5, 2), nullable=False, default=Decimal("1.00"))
    external_document_reference = Column(String(255), nullable=True)
    supporting_document_id = Column(
        Integer, ForeignKey("permanent_documents.id"), nullable=True, index=True
    )
    supporting_document = relationship("PermanentDocument", lazy="select")
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    def __repr__(self):
        return (
            f"<AnnualReportExpenseLine(id={self.id}, report_id={self.annual_report_id}, "
            f"category={self.category}, amount={self.amount})>"
        )


__all__ = [
    "AnnualReportExpenseLine",
    "ExpenseCategoryType",
]