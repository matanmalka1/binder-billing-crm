"""Annex (schedule) data lines for an annual report."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Text
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.utils.time_utils import utcnow


class AnnualReportAnnexData(Base):
    """Flexible per-schedule data line attached to an annual report."""

    __tablename__ = "annual_report_annex_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=False, index=True)
    schedule = Column(pg_enum(AnnualReportSchedule, create_type=False), nullable=False)
    line_number = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    data_version = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    def __repr__(self):
        return (
            f"<AnnualReportAnnexData(id={self.id}, report_id={self.annual_report_id}, "
            f"schedule={self.schedule}, line={self.line_number})>"
        )


__all__ = ["AnnualReportAnnexData"]
