from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus


class AdvancePaymentRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        business_id: int,
        year: int,
        month: int,
        due_date: date,
        expected_amount=None,
        paid_amount=None,
        tax_deadline_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        payment = AdvancePayment(
            business_id=business_id,
            year=year,
            month=month,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            tax_deadline_id=tax_deadline_id,
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

    def list_by_business_year(
        self,
        business_id: int,
        year: int,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AdvancePayment], int]:
        query = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.year == year,
                AdvancePayment.deleted_at.is_(None),
            )
            .order_by(AdvancePayment.month.asc())
        )
        if status:
            normalized = [s.value.lower() for s in status]
            query = query.filter(func.lower(AdvancePayment.status).in_(normalized))
        total = query.count()
        items = self._paginate(query, page, page_size)
        return items, total

    def exists_for_month(self, business_id: int, year: int, month: int) -> bool:
        return self.db.query(
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.year == year,
                AdvancePayment.month == month,
                AdvancePayment.deleted_at.is_(None),
            )
            .exists()
        ).scalar()

    def list_overview_payments(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> list[AdvancePayment]:
        query = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.year == year,
                AdvancePayment.deleted_at.is_(None),
            )
        )
        if month is not None:
            query = query.filter(AdvancePayment.month == month)
        if statuses:
            normalized = [s.value.lower() for s in statuses]
            query = query.filter(func.lower(AdvancePayment.status).in_(normalized))
        return query.all()

    def sum_paid_by_business_year(self, business_id: int, year: int) -> float:
        rows = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.year == year,
                func.lower(AdvancePayment.status) == AdvancePaymentStatus.PAID.value,
                AdvancePayment.deleted_at.is_(None),
            )
            .all()
        )
        return sum(float(p.paid_amount) for p in rows if p.paid_amount is not None)

    def update(self, payment: AdvancePayment, **fields) -> AdvancePayment:
        return self._update_entity(payment, touch_updated_at=True, **fields)

    def soft_delete(self, payment_id: int, deleted_by: int) -> bool:
        from app.utils.time_utils import utcnow
        payment = self.get_by_id(payment_id)
        if not payment:
            return False
        payment.deleted_at = utcnow()
        payment.deleted_by = deleted_by
        self.db.commit()
        return True