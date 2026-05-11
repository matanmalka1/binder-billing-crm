"""CRUD repository for AdvancePayment entities."""

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.advance_payments.models.advance_payment import (
    AdvancePayment,
    AdvancePaymentStatus,
)
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    AdvancePaymentAggregationRepository,
    advance_payment_status_text_expr,
)


class AdvancePaymentRepository(BaseRepository[AdvancePayment]):
    model = AdvancePayment

    def __init__(self, db: Session):
        super().__init__(db)
        self._agg = AdvancePaymentAggregationRepository(db)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create(
        self,
        client_record_id: int,
        period: str,
        period_months_count: int,
        due_date: date,
        expected_amount=None,
        paid_amount: Optional[Decimal] = None,
        payment_method=None,
        annual_report_id: Optional[int] = None,
        tax_calendar_entry_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        payment = AdvancePayment(
            client_record_id=client_record_id,
            period=period,
            period_months_count=period_months_count,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount if paid_amount is not None else Decimal("0"),
            payment_method=payment_method,
            annual_report_id=annual_report_id,
            tax_calendar_entry_id=tax_calendar_entry_id,
            notes=notes,
            status=AdvancePaymentStatus.PENDING,
        )
        self.db.add(payment)
        self.db.flush()
        return payment

    def get_by_id_for_client_record(
        self, payment_id: int, client_record_id: int
    ) -> Optional[AdvancePayment]:
        return self.db.scalars(
            select(AdvancePayment).where(
                AdvancePayment.id == payment_id,
                AdvancePayment.client_record_id == client_record_id,
                AdvancePayment.deleted_at.is_(None),
            )
        ).first()

    def list_by_client_record_year(
        self,
        client_record_id: int,
        year: int,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AdvancePayment], int]:
        base_where = [
            AdvancePayment.client_record_id == client_record_id,
            AdvancePayment.period.like(f"{year}-%"),
            AdvancePayment.deleted_at.is_(None),
        ]
        if status:
            normalized = [s.value.lower() for s in status]
            base_where.append(advance_payment_status_text_expr().in_(normalized))
        total = self.db.scalar(select(func.count(AdvancePayment.id)).where(*base_where))
        stmt = (
            select(AdvancePayment)
            .where(*base_where)
            .order_by(AdvancePayment.period.asc())
        )
        stmt = self.apply_pagination(stmt, page, page_size)
        items = list(self.db.scalars(stmt).all())
        return items, total

    def exists_for_period(self, client_record_id: int, period: str) -> bool:
        return self.db.scalar(
            select(
                exists(
                    select(AdvancePayment.id).where(
                        AdvancePayment.client_record_id == client_record_id,
                        AdvancePayment.period == period,
                        AdvancePayment.deleted_at.is_(None),
                    )
                )
            )
        )

    def get_by_period(
        self, client_record_id: int, period: str
    ) -> Optional[AdvancePayment]:
        return self.db.scalars(
            select(AdvancePayment).where(
                AdvancePayment.client_record_id == client_record_id,
                AdvancePayment.period == period,
                AdvancePayment.deleted_at.is_(None),
            )
        ).first()

    def update_payment(self, payment: AdvancePayment, **fields) -> AdvancePayment:
        return self._update_entity(payment, touch_updated_at=True, **fields)

    def soft_delete(self, payment_id: int, deleted_by: int | None = None) -> bool:
        return self._soft_delete_entity(payment_id, deleted_by)

    # ── Aggregation (delegated) ───────────────────────────────────────────────

    def sum_paid_by_client_year(self, client_record_id: int, year: int) -> float:
        return self._agg.sum_paid_by_client_year(client_record_id, year)

    def get_collections_aggregates(self, year: int, month=None) -> list:
        return self._agg.get_collections_aggregates(year, month)
