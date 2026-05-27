from __future__ import annotations

from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.enum_utils import pg_enum


class CreditPointReason(str, PyEnum):
    RESIDENT = "resident"  # תושב ישראל (2.25)
    ACADEMIC_DEGREE = "academic_degree"  # תואר אקדמי
    DISCHARGED_SOLDIER = "discharged_soldier"  # חייל משוחרר
    NEW_IMMIGRANT = "new_immigrant"  # עולה חדש
    SINGLE_PARENT = "single_parent"  # הורה יחיד


class AnnualReportCreditPoint(Base):
    __tablename__ = "annual_report_credit_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    annual_report_id: Mapped[int] = mapped_column(
        ForeignKey("annual_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[CreditPointReason] = mapped_column(
        pg_enum(CreditPointReason), nullable=False
    )
    points: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "annual_report_id",
            "reason",
            name="uq_credit_point_report_reason",
        ),
    )

    def __repr__(self):
        return (
            f"<AnnualReportCreditPoint(id={self.id}, "
            f"report_id={self.annual_report_id}, "
            f"reason='{self.reason}', points={self.points})>"
        )
