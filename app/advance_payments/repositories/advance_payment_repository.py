"""CRUD repository for AdvancePayment entities.

Aggregation/overview queries (list_overview_payments, sum_paid_by_business_year,
get_collections_aggregates) live in AdvancePaymentAggregationRepository.
This class re-exposes them via composition for backward compatibility.
"""

from datetime import date
from typing import Optional

from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow
from app.common.repositories import BaseRepository
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    AdvancePaymentAggregationRepository,
    advance_payment_status_text_expr,
)


class AdvancePaymentRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)
        self._agg = AdvancePaymentAggregationRepository(db)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create(
        self,
        business_id: int,
        period: str,
        period_months_count: int,
        due_date: date,
        expected_amount=None,
        paid_amount=None,
        payment_method=None,
        annual_report_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        payment = AdvancePayment(
            business_id=business_id,
            period=period,
            period_months_count=period_months_count,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            payment_method=payment_method,
            annual_report_id=annual_report_id,
            notes=notes,
            status=AdvancePaymentStatus.PENDING,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_by_id(self, payment_id: int) -> Optional[AdvancePayment]:
        return (
            self.db.query(AdvancePayment)
            .filter(AdvancePayment.id == payment_id, AdvancePayment.deleted_at.is_(None))
            .first()
        )

    def get_by_id_for_business(self, payment_id: int, business_id: int) -> Optional[AdvancePayment]:
        return (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.id == payment_id,
                AdvancePayment.business_id == business_id,
                AdvancePayment.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_business_year(
        self,
        business_id: int,
        year: int,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AdvancePayment], int]:
        """List payments for a business in a given year, filtered by period prefix."""
        query = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
            .order_by(AdvancePayment.period.asc())
        )
        if status:
            normalized = [s.value.lower() for s in status]
            query = query.filter(advance_payment_status_text_expr().in_(normalized))
        total = query.count()
        items = self._paginate(query, page, page_size)
        return items, total

    def exists_for_period(self, business_id: int, period: str) -> bool:
        """Check if a payment already exists for the given period."""
        return self.db.query(
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.period == period,
                AdvancePayment.deleted_at.is_(None),
            )
            .exists()
        ).scalar()

    def update(self, payment: AdvancePayment, **fields) -> AdvancePayment:
        return self._update_entity(payment, touch_updated_at=True, **fields)

    def soft_delete(self, payment_id: int, deleted_by: int) -> bool:
        payment = self.get_by_id(payment_id)
        if not payment:
            return False
        payment.deleted_at = utcnow()
        payment.deleted_by = deleted_by
        self.db.commit()
        return True

    # ── Aggregation (delegated) ───────────────────────────────────────────────

    def list_overview_payments(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> list[AdvancePayment]:
        return self._agg.list_overview_payments(year, month, statuses)

    def sum_paid_by_business_year(self, business_id: int, year: int) -> float:
        return self._agg.sum_paid_by_business_year(business_id, year)

    def get_collections_aggregates(self, year: int, month=None) -> list:
        return self._agg.get_collections_aggregates(year, month)
