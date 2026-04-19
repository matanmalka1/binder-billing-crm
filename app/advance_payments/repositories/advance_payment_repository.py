"""CRUD repository for AdvancePayment entities."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow
from app.common.repositories.base_repository import BaseRepository
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
        client_id: int,
        period: str,
        period_months_count: int,
        due_date: date,
        expected_amount=None,
        paid_amount=None,
        payment_method=None,
        annual_report_id: Optional[int] = None,
        notes: Optional[str] = None,
        client_record_id: Optional[int] = None,
    ) -> AdvancePayment:
        payment = AdvancePayment(
            client_id=client_id,
            client_record_id=client_record_id,
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
        self.db.flush()
        return payment

    def get_by_id(self, payment_id: int) -> Optional[AdvancePayment]:
        return (
            self.db.query(AdvancePayment)
            .filter(AdvancePayment.id == payment_id, AdvancePayment.deleted_at.is_(None))
            .first()
        )

    def get_by_id_for_client(self, payment_id: int, client_id: int) -> Optional[AdvancePayment]:
        return (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.id == payment_id,
                AdvancePayment.client_id == client_id,
                AdvancePayment.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_client_year(
        self,
        client_id: int,
        year: int,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AdvancePayment], int]:
        query = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.client_id == client_id,
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

    def list_by_client_record_year(
        self,
        client_record_id: int,
        year: int,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AdvancePayment], int]:
        query = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.client_record_id == client_record_id,
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

    def exists_for_period(self, client_id: int, period: str) -> bool:
        return self.db.query(
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.client_id == client_id,
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
        self.db.flush()
        return True

    # ── Aggregation (delegated) ───────────────────────────────────────────────

    def sum_paid_by_client_year(self, client_id: int, year: int) -> float:
        return self._agg.sum_paid_by_client_year(client_id, year)

    def get_collections_aggregates(self, year: int, month=None) -> list:
        return self._agg.get_collections_aggregates(year, month)
