from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import (
    advance_payment_status_text_expr,
)


class AdvancePaymentAnalyticsRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def get_annual_kpis(self, business_id: int, year: int) -> dict:
        rows = (
            self.db.query(
                AdvancePayment.status,
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label("total_expected"),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label("total_paid"),
                func.count(AdvancePayment.id).label("count"),
            )
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
            .group_by(AdvancePayment.status)
            .all()
        )
        return {
            "total_expected": sum(float(r.total_expected) for r in rows),
            "total_paid": sum(float(r.total_paid) for r in rows),
            "overdue_count": sum(r.count for r in rows if r.status == AdvancePaymentStatus.OVERDUE),
            "on_time_count": sum(r.count for r in rows if r.status == AdvancePaymentStatus.PAID),
        }

    def get_overview_kpis(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> dict:
        query = self.db.query(
            func.coalesce(func.sum(AdvancePayment.expected_amount), 0),
            func.coalesce(func.sum(AdvancePayment.paid_amount), 0),
        ).filter(
            AdvancePayment.period.like(f"{year}-%"),
            AdvancePayment.deleted_at.is_(None),
        )
        if month is not None:
            query = query.filter(AdvancePayment.period == f"{year}-{month:02d}")
        if statuses:
            normalized = [s.value.lower() for s in statuses]
            query = query.filter(advance_payment_status_text_expr().in_(normalized))
        total_expected, total_paid = query.one()
        return {
            "total_expected": float(total_expected),
            "total_paid": float(total_paid),
        }

    def monthly_chart_data(self, business_id: int, year: int) -> list[dict]:
        rows = (
            self.db.query(
                AdvancePayment.period,
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label("expected_amount"),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label("paid_amount"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                advance_payment_status_text_expr() == AdvancePaymentStatus.OVERDUE.value,
                                AdvancePayment.expected_amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("overdue_amount"),
            )
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
            .group_by(AdvancePayment.period)
            .all()
        )
        by_period = {r.period: r for r in rows}
        return [
            {
                "period": f"{year}-{m:02d}",
                "expected_amount": float(by_period[f"{year}-{m:02d}"].expected_amount) if f"{year}-{m:02d}" in by_period else 0.0,
                "paid_amount": float(by_period[f"{year}-{m:02d}"].paid_amount) if f"{year}-{m:02d}" in by_period else 0.0,
                "overdue_amount": float(by_period[f"{year}-{m:02d}"].overdue_amount) if f"{year}-{m:02d}" in by_period else 0.0,
            }
            for m in range(1, 13)
        ]
