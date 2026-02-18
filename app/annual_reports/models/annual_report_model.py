"""Annual income tax report ORM model."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)

from app.database import Base
from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.utils.time import utcnow


class AnnualReport(Base):
    """
    Annual income tax report for a single client and tax year.

    The required ITA form is derived from the client_type at creation time.
    """

    __tablename__ = "annual_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)  # responsible advisor

    # Core identity
    tax_year = Column(Integer, nullable=False)  # e.g. 2023
    client_type = Column(Enum(ClientTypeForReport), nullable=False)
    form_type = Column(Enum(AnnualReportForm), nullable=False)

    # Status
    status = Column(
        Enum(AnnualReportStatus),
        default=AnnualReportStatus.NOT_STARTED,
        nullable=False,
    )

    # Deadlines
    deadline_type = Column(Enum(DeadlineType), default=DeadlineType.STANDARD, nullable=False)
    filing_deadline = Column(DateTime, nullable=True)  # computed at creation; may be overridden
    custom_deadline_note = Column(String, nullable=True)

    # Filing outcome
    submitted_at = Column(DateTime, nullable=True)
    ita_reference = Column(String, nullable=True)  # מספר אסמכתא ממס הכנסה
    assessment_amount = Column(Numeric(14, 2), nullable=True)  # סכום השומה
    refund_due = Column(Numeric(14, 2), nullable=True)  # החזר מס
    tax_due = Column(Numeric(14, 2), nullable=True)  # תשלום נוסף

    # Flags
    has_rental_income = Column(Boolean, default=False, nullable=False)  # triggers Schedule B
    has_capital_gains = Column(Boolean, default=False, nullable=False)  # triggers Schedule Bet
    has_foreign_income = Column(Boolean, default=False, nullable=False)  # triggers Schedule Gimmel
    has_depreciation = Column(Boolean, default=False, nullable=False)  # triggers Schedule Dalet
    has_exempt_rental = Column(Boolean, default=False, nullable=False)  # triggers Schedule Heh

    # Free-form notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_annual_report_client_year", "client_id", "tax_year", unique=True),
        Index("idx_annual_report_status", "status"),
        Index("idx_annual_report_deadline", "filing_deadline"),
        Index("idx_annual_report_assigned", "assigned_to"),
    )

    def __repr__(self):
        return (
            f"<AnnualReport(id={self.id}, client_id={self.client_id}, "
            f"year={self.tax_year}, form={self.form_type}, status='{self.status}')>"
        )


__all__ = ["AnnualReport"]