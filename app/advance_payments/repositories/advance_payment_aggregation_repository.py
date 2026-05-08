"""Aggregation and overview queries for AdvancePayment entities."""

from typing import Optional

from sqlalchemy import Integer, String, case, cast, func
from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients
from app.common.repositories.base_repository import BaseRepository
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus



def advance_payment_status_text_expr():
    """
    Normalize enum-backed status columns to lowercase text.

    SQLite stores enums as strings, but PostgreSQL keeps a native enum type.
    Casting avoids `lower(enum_type)` errors on PostgreSQL while preserving the
    case-insensitive matching used for legacy SQLite fixtures.
    """
    return func.lower(cast(AdvancePayment.status, String))


def advance_payment_start_month_expr():
    return cast(func.substr(AdvancePayment.period, 6, 2), Integer)


def advance_payment_matches_month_expr(month: int):
    start_month = advance_payment_start_month_expr()
    end_month = start_month + AdvancePayment.period_months_count - 1
    return (start_month <= month) & (end_month >= month)


class AdvancePaymentAggregationRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def list_overview_payments(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> list[AdvancePayment]:
        query = (
            scope_to_active_clients(self.db.query(AdvancePayment), AdvancePayment)
            .filter(
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
        )
        if month is not None:
            query = query.filter(advance_payment_matches_month_expr(month))
        if statuses:
            normalized = [s.value.lower() for s in statuses]
            query = query.filter(advance_payment_status_text_expr().in_(normalized))
        return query.all()

    def sum_paid_by_client_year(self, client_record_id: int, year: int) -> float:
        result = (
            self.db.query(func.coalesce(func.sum(AdvancePayment.paid_amount), 0))
            .filter(
                AdvancePayment.client_record_id == client_record_id,
                AdvancePayment.period.like(f"{year}-%"),
                advance_payment_status_text_expr() == AdvancePaymentStatus.PAID.value,
                AdvancePayment.deleted_at.is_(None),
            )
            .scalar()
        )
        return float(result)

    def get_collections_aggregates(self, year: int, month=None) -> list:
        """Per-client aggregates for the collections report."""
        today_expr = func.current_date()
        query = (
            scope_to_active_clients(
                self.db.query(
                    AdvancePayment.client_record_id,
                    func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label("total_expected"),
                    func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label("total_paid"),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    (AdvancePayment.due_date < today_expr)
                                    & (advance_payment_status_text_expr() != AdvancePaymentStatus.PAID.value),
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("overdue_count"),
                ),
                AdvancePayment,
            )
            .filter(
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
        )
        if month is not None:
            query = query.filter(advance_payment_matches_month_expr(month))
        return query.group_by(AdvancePayment.client_record_id).all()

    def batch_summary_by_month(self, year: int) -> list:
        """Per-month aggregates: client_count, overdue_count, missing_turnover_count, totals.

        Groups by (start_month, period_months_count) so monthly and bimonthly
        batches for the same start month are not merged.
        due_date is taken from the payments' stored due_date (sourced from TaxCalendarEntry).
        """
        today_expr = func.current_date()
        start_month = advance_payment_start_month_expr()
        return (
            scope_to_active_clients(
                self.db.query(
                    start_month.label("month"),
                    AdvancePayment.period_months_count,
                    func.max(AdvancePayment.due_date).label("due_date"),
                    func.count(AdvancePayment.id).label("client_count"),
                    func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label("total_expected"),
                    func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label("total_paid"),
                    func.sum(
                        case(
                            (
                                (AdvancePayment.due_date < today_expr)
                                & (advance_payment_status_text_expr() != AdvancePaymentStatus.PAID.value),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("overdue_count"),
                    func.sum(
                        case(
                            (
                                AdvancePayment.reported_turnover.is_(None)
                                & AdvancePayment.turnover_source_vat_work_item_id.is_(None),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("snapshot_missing_count"),
                    func.sum(
                        case(
                            (
                                advance_payment_status_text_expr() == AdvancePaymentStatus.PENDING.value,
                                1,
                            ),
                            else_=0,
                        )
                    ).label("pending_count"),
                ),
                AdvancePayment,
            )
            .filter(
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
            .group_by(start_month, AdvancePayment.period_months_count)
            .order_by(start_month, AdvancePayment.period_months_count)
            .all()
        )
