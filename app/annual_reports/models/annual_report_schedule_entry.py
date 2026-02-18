"""Annual report schedule entries (annex tracking)."""

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, Text

from app.database import Base
from app.models.annual_reports.annual_report_enums import AnnualReportSchedule
from app.utils.time import utcnow


class AnnualReportScheduleEntry(Base):
    """
    Tracks required schedules for an annual report and their completion status.
    """

    __tablename__ = "annual_report_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=False, index=True)

    schedule = Column(Enum(AnnualReportSchedule), nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_schedule_entry_report", "annual_report_id"),
    )


__all__ = ["AnnualReportScheduleEntry"]
