from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_credit_point_reason import (
    AnnualReportCreditPoint,
    CreditPointReason,
)


_ZERO = Decimal("0")
# Israeli resident baseline (תושב ישראל). Intentionally static — does not vary
# year-to-year; callers supply actual points from the report's credit-point rows.
_DEFAULT_RESIDENT_CREDIT_POINTS = Decimal("2.25")
_TUITION_REASONS = frozenset({
    CreditPointReason.ACADEMIC_DEGREE,
})


class AnnualReportCreditPointRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_report_id(self, report_id: int) -> list[AnnualReportCreditPoint]:
        return (
            self.db.query(AnnualReportCreditPoint)
            .filter(AnnualReportCreditPoint.annual_report_id == report_id)
            .order_by(AnnualReportCreditPoint.id.asc())
            .all()
        )

    def create(
        self,
        annual_report_id: int,
        reason: CreditPointReason,
        points: Decimal,
        notes: Optional[str] = None,
    ) -> AnnualReportCreditPoint:
        row = AnnualReportCreditPoint(
            annual_report_id=annual_report_id,
            reason=reason,
            points=points,
            notes=notes,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def aggregate_breakdown(self, report_id: int) -> dict[str, Decimal]:
        rows = self.list_by_report_id(report_id)
        if not rows:
            return {
                "credit_points": _DEFAULT_RESIDENT_CREDIT_POINTS,
                "pension_credit_points": _ZERO,
                "life_insurance_credit_points": _ZERO,
                "tuition_credit_points": _ZERO,
                "total_credit_points": _DEFAULT_RESIDENT_CREDIT_POINTS,
            }

        base = _ZERO
        tuition = _ZERO
        pension = _ZERO
        life_insurance = _ZERO
        total = _ZERO

        for row in rows:
            total += Decimal(str(row.points))
            if row.reason in _TUITION_REASONS:
                tuition += Decimal(str(row.points))
            else:
                base += Decimal(str(row.points))

        return {
            "credit_points": base,
            "pension_credit_points": pension,
            "life_insurance_credit_points": life_insurance,
            "tuition_credit_points": tuition,
            "total_credit_points": total,
        }

    def total_points_by_report_id(self, report_id: int) -> Decimal:
        total = (
            self.db.query(func.coalesce(func.sum(AnnualReportCreditPoint.points), 0))
            .filter(AnnualReportCreditPoint.annual_report_id == report_id)
            .scalar()
        )
        if total in (None, 0):
            return _DEFAULT_RESIDENT_CREDIT_POINTS
        return Decimal(str(total))


__all__ = ["AnnualReportCreditPointRepository"]
