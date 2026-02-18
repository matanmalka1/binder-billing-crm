"""Append-only status history for annual reports."""

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text

from app.database import Base
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.utils.time import utcnow


class AnnualReportStatusHistory(Base):
    """Audit trail for every status change on an annual report."""

    __tablename__ = "annual_report_status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=False, index=True)

    from_status = Column(Enum(AnnualReportStatus), nullable=True)  # null on first entry
    to_status = Column(Enum(AnnualReportStatus), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_by_name = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_status_history_report", "annual_report_id"),
    )


__all__ = ["AnnualReportStatusHistory"]