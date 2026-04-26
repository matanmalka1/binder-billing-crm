"""Append-only status history for annual reports."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.utils.time_utils import utcnow


class AnnualReportStatusHistory(Base):
    """Audit trail for every status change on an annual report.

    Append-only — no soft delete, no updated_at.
    """

    __tablename__ = "annual_report_status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=False, index=True)
    from_status = Column(pg_enum(AnnualReportStatus), nullable=True)
    to_status = Column(pg_enum(AnnualReportStatus), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=utcnow)

__all__ = ["AnnualReportStatusHistory"]
