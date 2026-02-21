from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, Text

from app.database import Base
from app.utils.time import utcnow


class AnnualReportDetail(Base):
    __tablename__ = "annual_report_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(
        Integer, ForeignKey("annual_reports.id"), nullable=False, unique=True, index=True
    )
    tax_refund_amount = Column(Numeric(10, 2), nullable=True)
    tax_due_amount = Column(Numeric(10, 2), nullable=True)
    client_approved_at = Column(DateTime, nullable=True)
    internal_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    def __repr__(self):
        return (
            f"<AnnualReportDetail(id={self.id}, report_id={self.report_id})>"
        )
