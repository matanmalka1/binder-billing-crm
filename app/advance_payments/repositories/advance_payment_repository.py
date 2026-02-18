from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.utils.time import utcnow


class AdvancePaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_client_year(self, client_id: int, year: int) -> list[AdvancePayment]:
        return (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.client_id == client_id,
                AdvancePayment.year == year,
            )
            .order_by(AdvancePayment.month.asc())
            .all()
        )

    def get_by_id(self, id: int) -> Optional[AdvancePayment]:
        return self.db.query(AdvancePayment).filter(AdvancePayment.id == id).first()

    def update(self, id: int, **fields) -> Optional[AdvancePayment]:
        payment = self.get_by_id(id)
        if payment is None:
            return None
        for key, value in fields.items():
            if hasattr(payment, key):
                setattr(payment, key, value)
        payment.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(payment)
        return payment

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
