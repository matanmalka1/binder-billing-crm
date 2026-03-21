from enum import Enum as PyEnum

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, UniqueConstraint
from app.utils.enum_utils import pg_enum

from app.database import Base


class CreditPointReason(str, PyEnum):
    RESIDENT           = "resident"            # תושב ישראל (2.25)
    ACADEMIC_DEGREE    = "academic_degree"     # תואר אקדמי
    DISCHARGED_SOLDIER = "discharged_soldier"  # חייל משוחרר
    NEW_IMMIGRANT      = "new_immigrant"       # עולה חדש
    SINGLE_PARENT      = "single_parent"       # הורה יחיד


class AnnualReportCreditPoint(Base):
    __tablename__ = "annual_report_credit_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=False, index=True)
    reason = Column(pg_enum(CreditPointReason), nullable=False)
    points = Column(Numeric(5, 2), nullable=False)
    notes  = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "annual_report_id", "reason",
            name="uq_credit_point_report_reason",
        ),
    )

    def __repr__(self):
        return (
            f"<AnnualReportCreditPoint(id={self.id}, "
            f"report_id={self.annual_report_id}, "
            f"reason='{self.reason}', points={self.points})>"
        )
