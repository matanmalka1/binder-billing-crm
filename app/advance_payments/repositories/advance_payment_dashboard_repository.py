from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import (
    AdvancePayment,
    AdvancePaymentStatus,
)
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    advance_payment_status_text_expr,
)
from app.clients.repositories.active_client_scope import scope_to_active_clients
from app.common.repositories.base_repository import BaseRepository


class AdvancePaymentDashboardRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def completion_for_period(
        self, period: str, period_months_count: int
    ) -> tuple[int, int]:
        paid_expr = case(
            (advance_payment_status_text_expr() == AdvancePaymentStatus.PAID.value, 1),
            else_=0,
        )
        completed, total = (
            scope_to_active_clients(
                self.db.query(
                    func.coalesce(func.sum(paid_expr), 0),
                    func.count(AdvancePayment.id),
                ),
                AdvancePayment,
            )
            .filter(
                AdvancePayment.period == period,
                AdvancePayment.period_months_count == period_months_count,
                AdvancePayment.deleted_at.is_(None),
            )
            .one()
        )
        return int(completed or 0), int(total or 0)
