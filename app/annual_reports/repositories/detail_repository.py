from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_detail import AnnualReportDetail

_CACHE_COLUMNS = frozenset({
    "credit_points",
    "pension_credit_points",
    "life_insurance_credit_points",
    "tuition_credit_points",
})

_META_COLUMNS = frozenset({
    "client_approved_at",
    "internal_notes",
    "amendment_reason",
    "pension_contribution",
    "donation_amount",
    "other_credits",
})


class AnnualReportDetailRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_report_id(self, report_id: int) -> Optional[AnnualReportDetail]:
        return (
            self.db.query(AnnualReportDetail)
            .filter(AnnualReportDetail.report_id == report_id)
            .first()
        )

    def refresh_credit_cache(
        self,
        report_id: int,
        credit_points: Optional[Decimal],
        pension_credit_points: Optional[Decimal],
        life_insurance_credit_points: Optional[Decimal],
        tuition_credit_points: Optional[Decimal],
    ) -> AnnualReportDetail:
        """Update only the computed credit point cache columns."""
        return self._upsert(report_id, {
            "credit_points": credit_points,
            "pension_credit_points": pension_credit_points,
            "life_insurance_credit_points": life_insurance_credit_points,
            "tuition_credit_points": tuition_credit_points,
        }, allowed=_CACHE_COLUMNS)

    def update_meta(self, report_id: int, **fields) -> AnnualReportDetail:
        """Update only business metadata columns (approval, notes, amendment reason, deductions)."""
        return self._upsert(report_id, fields, allowed=_META_COLUMNS)

    def _upsert(
        self, report_id: int, fields: dict, allowed: frozenset
    ) -> AnnualReportDetail:
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(
                f"AnnualReportDetailRepository: unexpected columns {unknown}. "
                f"Use the correct method for cache vs metadata writes."
            )
        detail = self.get_by_report_id(report_id)
        if detail is None:
            detail = AnnualReportDetail(report_id=report_id, **fields)
            self.db.add(detail)
        else:
            for key, value in fields.items():
                setattr(detail, key, value)
        self.db.commit()
        self.db.refresh(detail)
        return detail


__all__ = ["AnnualReportDetailRepository"]
