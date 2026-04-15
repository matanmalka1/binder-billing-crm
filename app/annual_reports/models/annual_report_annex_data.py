"""Annex (schedule) data lines for an annual report."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Text, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utcnow


class AnnualReportAnnexData(Base):
    """Flexible per-schedule data line attached to an annual report."""

    __tablename__ = "annual_report_annex_data"
    __table_args__ = (
        UniqueConstraint("schedule_entry_id", "line_number", name="uq_annual_report_annex_data_schedule_entry_line"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_entry_id = Column(
        Integer,
        ForeignKey("annual_report_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    data_version = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)
    schedule_entry = relationship("AnnualReportScheduleEntry", back_populates="annex_lines")

    @hybrid_property
    def annual_report_id(self):
        return self.schedule_entry.annual_report_id

    @hybrid_property
    def schedule(self):
        return self.schedule_entry.schedule

    def __repr__(self):
        return (
            f"<AnnualReportAnnexData(id={self.id}, report_id={self.annual_report_id}, "
            f"schedule={self.schedule}, line={self.line_number})>"
        )


__all__ = ["AnnualReportAnnexData"]
