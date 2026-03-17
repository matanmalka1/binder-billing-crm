from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus


class AdvancePaymentRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

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
                AdvancePayment.year == year,
            )
            .order_by(AdvancePayment.month.asc())
        )
        if status is not None:
            query = query.filter(AdvancePayment.status.in_(status))
        total = query.count()
        items = self._paginate(query, page, page_size)
        return items, total

    def get_by_id(self, id: int) -> Optional[AdvancePayment]:
        return self.db.query(AdvancePayment).filter(AdvancePayment.id == id).first()

    def exists_for_month(self, client_id: int, year: int, month: int) -> bool:
        return self.db.query(
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.client_id == client_id,
                AdvancePayment.year == year,
                AdvancePayment.month == month,
            )
            .exists()
        ).scalar()

    def update(self, payment: AdvancePayment, **fields) -> AdvancePayment:
        return self._update_entity(payment, touch_updated_at=True, **fields)

    def delete(self, payment: AdvancePayment) -> None:
        self.db.delete(payment)
        self.db.commit()

    def list_overview_payments(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> list[AdvancePayment]:
        """Return all matching AdvancePayment rows (no cross-domain join)."""
        query = (
            self.db.query(AdvancePayment)
            .filter(AdvancePayment.year == year)
        )
        if month is not None:
            query = query.filter(AdvancePayment.month == month)
        if statuses:
            query = query.filter(AdvancePayment.status.in_(statuses))
        return query.all()

    def sum_paid_by_client_year(self, client_id: int, year: int) -> float:
        """Sum paid_amount for all PAID advance payments for a client/year."""
        rows = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.client_id == client_id,
                AdvancePayment.year == year,
                AdvancePayment.status == AdvancePaymentStatus.PAID,
            )
            .all()
        )
        return sum(float(p.paid_amount) for p in rows if p.paid_amount is not None)

    def create(
        self,
        client_id: int,
        year: int,
        month: int,
        due_date: date,
        expected_amount=None,
        paid_amount=None,
        tax_deadline_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        payment = AdvancePayment(
            client_id=client_id,
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
