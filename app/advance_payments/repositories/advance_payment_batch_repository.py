from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import (
    AdvancePayment,
    AdvancePaymentStatus,
)
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    advance_payment_start_month_expr,
    advance_payment_status_text_expr,
)
from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.repositories.base_repository import BaseRepository


class AdvancePaymentBatchRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def batch_summary_by_month(self, year: int) -> list:
        today_expr = func.current_date()
        start_month = advance_payment_start_month_expr()
        stmt = (
            scope_to_active_clients_stmt(
                select(
                    start_month.label("month"),
                    AdvancePayment.period_months_count,
                    func.max(AdvancePayment.due_date).label("due_date"),
                    func.count(AdvancePayment.id).label("client_count"),
                    func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label(
                        "total_expected"
                    ),
                    func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label(
                        "total_paid"
                    ),
                    func.coalesce(
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
                        ),
                        0,
                    ).label("overdue_count"),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    AdvancePayment.reported_turnover.is_(None)
                                    & AdvancePayment.turnover_source_vat_work_item_id.is_(
                                        None
                                    ),
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("snapshot_missing_count"),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    advance_payment_status_text_expr()
                                    == AdvancePaymentStatus.PENDING.value,
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("pending_count"),
                ),
                AdvancePayment,
            )
            .where(
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
            .group_by(start_month, AdvancePayment.period_months_count)
            .order_by(start_month, AdvancePayment.period_months_count)
        )
        return self.db.execute(stmt).all()
