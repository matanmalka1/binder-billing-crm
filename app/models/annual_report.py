from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Index

from app.database import Base
from app.utils.time import utcnow


class ReportStage(str, PyEnum):
    MATERIAL_COLLECTION = "material_collection"
    IN_PROGRESS = "in_progress"
    FINAL_REVIEW = "final_review"
    CLIENT_SIGNATURE = "client_signature"
    TRANSMITTED = "transmitted"


class AnnualReport(Base):
    __tablename__ = "annual_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    tax_year = Column(Integer, nullable=False)
    stage = Column(
        Enum(ReportStage),
        default=ReportStage.MATERIAL_COLLECTION,
        nullable=False,
    )
    status = Column(String, default="not_started", nullable=False)

    # Dates
    created_at = Column(DateTime, default=utcnow, nullable=False)
    due_date = Column(Date, nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    # Metadata
    form_type = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_annual_report_client_year", "client_id", "tax_year", unique=True),
        Index("idx_annual_report_stage", "stage"),
        Index("idx_annual_report_due_date", "due_date"),
    )

    def __repr__(self):
        return (
            f"<AnnualReport(id={self.id}, client_id={self.client_id}, "
            f"tax_year={self.tax_year}, stage='{self.stage}')>"
        )