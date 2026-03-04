from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.utils.time import utcnow


class AdvancePaymentRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def list_by_client_year(
        self,
        client_id: int,
        year: int,
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
        total = query.count()
        items = self._paginate(query, page, page_size)
        return items, total

    def get_by_id(self, id: int) -> Optional[AdvancePayment]:
        return self.db.query(AdvancePayment).filter(AdvancePayment.id == id).first()

    def update(self, id: int, **fields) -> Optional[AdvancePayment]:
        payment = self.get_by_id(id)
        return self._update_entity(payment, touch_updated_at=True, **fields)

    def get_annual_output_vat(self, client_id: int, year: int) -> Optional[Decimal]:
        """Sum total_output_vat for all VatWorkItems in a given year for a client.
        Returns None if no work items exist for that year."""
        from app.vat_reports.models.vat_work_item import VatWorkItem

        prefix = f"{year}-%"
        result = (
            self.db.query(func.sum(VatWorkItem.total_output_vat))
            .filter(
                VatWorkItem.client_id == client_id,
                VatWorkItem.period.like(prefix),
            )
            .scalar()
        )
        if result is None:
            return None
        return Decimal(str(result))

    def create(
        self,
        client_id: int,
        year: int,
        month: int,
        due_date: date,
        expected_amount=None,
        paid_amount=None,
        tax_deadline_id: Optional[int] = None,
    ) -> AdvancePayment:
        payment = AdvancePayment(
            client_id=client_id,
            year=year,
            month=month,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            tax_deadline_id=tax_deadline_id,
            status=AdvancePaymentStatus.PENDING,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment
