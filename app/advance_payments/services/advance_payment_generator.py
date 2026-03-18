from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import NotFoundError


def generate_annual_schedule(
    client_id: int,
    year: int,
    db: Session,
) -> tuple[list[AdvancePayment], int]:
    """
    Create 12 advance payment records (months 1–12) for the given client/year.
    Due date: 15th of each month (Israeli standard).
    Skips months that already have a record (idempotent).
    Returns (created_records, skipped_count).
    """
    if not ClientRepository(db).get_by_id(client_id):
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "ADVANCE_PAYMENT.CLIENT_NOT_FOUND")

    service = AdvancePaymentService(db)
    repo = AdvancePaymentRepository(db)

    suggested: Optional[Decimal] = service.suggest_expected_amount(client_id, year)

    created: list[AdvancePayment] = []
    skipped = 0

    for month in range(1, 13):
        if repo.exists_for_month(client_id, year, month):
            skipped += 1
            continue
        payment = repo.create(
            client_id=client_id,
            year=year,
            month=month,
            due_date=date(year, month, 15),
            expected_amount=suggested,
        )
        created.append(payment)

    return created, skipped
