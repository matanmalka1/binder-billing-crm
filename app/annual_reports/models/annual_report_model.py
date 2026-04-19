from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Index, Integer, Numeric, String, Text, text,
)
from sqlalchemy.orm import relationship
from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow
from app.annual_reports.models.annual_report_enums import (
    ClientAnnualFilingType,
    PrimaryAnnualReportForm,
    AnnualReportStatus,
    FilingDeadlineType,
    SubmissionMethod,
    ExtensionReason
)
 
 
# ─── AnnualReport ─────────────────────────────────────────────────────────────
 
class AnnualReport(Base):
    __tablename__ = "annual_reports"
 
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    client_record_id = Column(Integer, ForeignKey("client_records.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
 
    tax_year = Column(Integer, nullable=False)
    client_type = Column(pg_enum(ClientAnnualFilingType), nullable=False)
    # Snapshot of the main annual-return form derived from client_type at creation.
    form_type = Column(pg_enum(PrimaryAnnualReportForm), nullable=False)
    status = Column(pg_enum(AnnualReportStatus), default=AnnualReportStatus.NOT_STARTED, nullable=False)
 
    deadline_type = Column(pg_enum(FilingDeadlineType), default=FilingDeadlineType.STANDARD, nullable=False)
    filing_deadline = Column(DateTime, nullable=True)
    custom_deadline_note = Column(String, nullable=True)
 
    submitted_at = Column(DateTime, nullable=True)
    ita_reference = Column(String, nullable=True)
    assessment_amount = Column(Numeric(14, 2), nullable=True)
    refund_due = Column(Numeric(14, 2), nullable=True)
    tax_due = Column(Numeric(14, 2), nullable=True)
 
    has_rental_income = Column(Boolean, default=False, nullable=False)
    has_capital_gains = Column(Boolean, default=False, nullable=False)
    has_foreign_income = Column(Boolean, default=False, nullable=False)
    has_depreciation = Column(Boolean, default=False, nullable=False)
    has_exempt_rental = Column(Boolean, default=False, nullable=False)
  
    submission_method = Column(pg_enum(SubmissionMethod), nullable=True)
    extension_reason  = Column(pg_enum(ExtensionReason),  nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    detail = relationship(
        "AnnualReportDetail", back_populates="report",
        uselist=False, cascade="all, delete-orphan",
    )
    schedule_entries = relationship(
        "AnnualReportScheduleEntry", back_populates="annual_report",
        cascade="all, delete-orphan",
    )
    income_lines = relationship(
        "AnnualReportIncomeLine", cascade="all, delete-orphan",
    )
    expense_lines = relationship(
        "AnnualReportExpenseLine", cascade="all, delete-orphan",
    )
    credit_points = relationship(
        "AnnualReportCreditPoint", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "idx_annual_report_client_year_type",
            "client_id",
            "tax_year",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index("idx_annual_report_status", "status"),
        Index("idx_annual_report_deadline", "filing_deadline"),
        Index("idx_annual_report_assigned", "assigned_to"),
    )

    def __repr__(self):
        return (
            f"<AnnualReport(id={self.id}, client_id={self.client_id}, "
            f"year={self.tax_year}, status='{self.status}')>"
        )
