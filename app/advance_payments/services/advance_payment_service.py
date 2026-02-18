from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.clients.repositories.client_repository import ClientRepository


class AdvancePaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdvancePaymentRepository(db)
        self.client_repo = ClientRepository(db)

    def list_payments(self, client_id: int, year: int) -> list[AdvancePayment]:
        return self.repo.list_by_client_year(client_id, year)

    def update_payment(self, payment_id: int, **fields) -> AdvancePayment:
        payment = self.repo.get_by_id(payment_id)
        if not payment:
            raise ValueError(f"Advance payment {payment_id} not found")

        if "status" in fields and fields["status"] is not None:
            try:
                AdvancePaymentStatus(fields["status"])
            except ValueError:
                raise ValueError(
                    f"Invalid status: {fields['status']}. "
                    f"Must be one of: pending, paid, partial, overdue"
                )

        updated = self.repo.update(payment_id, **fields)
        return updated
