from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import (
    advance_payment_status_text_expr,
)
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    advance_payment_matches_month_expr,
)


class AdvancePaymentAnalyticsRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def get_annual_kpis_for_client(self, client_id: int, year: int) -> dict:
        rows = (
            self.db.query(
                AdvancePayment.status,
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label("total_expected"),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label("total_paid"),
                func.count(AdvancePayment.id).label("count"),
            )
            .filter(
                AdvancePayment.client_id == client_id,
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
            query = query.filter(advance_payment_matches_month_expr(month))
        if statuses:
            normalized = [s.value.lower() for s in statuses]
            query = query.filter(advance_payment_status_text_expr().in_(normalized))
        total_expected, total_paid = query.one()
        return {
            "total_expected": float(total_expected),
            "total_paid": float(total_paid),
        }

    def monthly_chart_data_for_client(self, client_id: int, year: int) -> list[dict]:
        rows = (
            self.db.query(
                AdvancePayment.period,
                AdvancePayment.period_months_count,
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
                AdvancePayment.client_id == client_id,
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
            .group_by(AdvancePayment.period, AdvancePayment.period_months_count)
            .order_by(AdvancePayment.period.asc())
            .all()
        )
        return [
            {
                "period": r.period,
                "period_months_count": int(r.period_months_count),
                "expected_amount": float(r.expected_amount),
                "paid_amount": float(r.paid_amount),
                "overdue_amount": float(r.overdue_amount),
            }
            for r in rows
        ]
