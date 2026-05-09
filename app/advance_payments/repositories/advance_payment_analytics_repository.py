from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.repositories.base_repository import BaseRepository
from app.advance_payments.models.advance_payment import (
    AdvancePayment,
    AdvancePaymentStatus,
)
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    advance_payment_matches_month_expr,
    advance_payment_status_text_expr,
)


class AdvancePaymentAnalyticsRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def get_annual_kpis_for_client(self, client_record_id: int, year: int) -> dict:
        today_expr = func.current_date()
        rows = self.db.execute(
            select(
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label(
                    "total_expected"
                ),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label(
                    "total_paid"
                ),
                func.count(AdvancePayment.id).label("total_count"),
                func.sum(
                    case(
                        (
                            (AdvancePayment.due_date < today_expr)
                            & (
                                advance_payment_status_text_expr()
                                != AdvancePaymentStatus.PAID.value
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("overdue_count"),
                func.sum(
                    case(
                        (
                            advance_payment_status_text_expr()
                            == AdvancePaymentStatus.PAID.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label("on_time_count"),
            ).where(
                AdvancePayment.client_record_id == client_record_id,
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
        ).one()
        return {
            "total_expected": float(rows.total_expected),
            "total_paid": float(rows.total_paid),
            "overdue_count": int(rows.overdue_count or 0),
            "on_time_count": int(rows.on_time_count or 0),
        }

    def get_overview_kpis(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> dict:
        stmt = scope_to_active_clients_stmt(
            select(
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0),
            ),
            AdvancePayment,
        ).where(
            AdvancePayment.period.like(f"{year}-%"),
            AdvancePayment.deleted_at.is_(None),
        )
        if month is not None:
            stmt = stmt.where(advance_payment_matches_month_expr(month))
        if statuses:
            normalized = [s.value.lower() for s in statuses]
            stmt = stmt.where(advance_payment_status_text_expr().in_(normalized))
        total_expected, total_paid = self.db.execute(stmt).one()
        return {
            "total_expected": float(total_expected),
            "total_paid": float(total_paid),
        }
