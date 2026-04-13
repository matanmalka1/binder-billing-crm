from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.constants import build_due_date, get_period_start_months
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import NotFoundError


def generate_annual_schedule(
    client_id: int,
    year: int,
    db: Session,
    period_months_count: int = 1,
) -> tuple[list[AdvancePayment], int]:
    """
    יוצר רשומות מקדמה ללקוח ולשנה נתונים.
    - period_months_count=1: 12 רשומות חודשיות (YYYY-MM)
    - period_months_count=2: 6 רשומות דו-חודשיות (YYYY-MM של חודש ראשון)
    תאריך יעד: ה-15 לחודש שאחרי התקופה.
    מדלג על תקופות שכבר קיימות (אידמפוטנטי).
    מחזיר (created_records, skipped_count).
    """
    client = ClientRepository(db).get_by_id(client_id)
    if not client:
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "ADVANCE_PAYMENT.CLIENT_NOT_FOUND")

    service = AdvancePaymentService(db)
    repo = AdvancePaymentRepository(db)
    suggested: Optional[Decimal] = service.suggest_expected_amount_for_client(
        client_id, year, period_months_count
    )

    start_months = get_period_start_months(period_months_count)

    created: list[AdvancePayment] = []
    skipped = 0

    for month in start_months:
        period = f"{year}-{month:02d}"
        if repo.exists_for_period(client_id, period):
            skipped += 1
            continue

        payment = repo.create(
            client_id=client_id,
            period=period,
            period_months_count=period_months_count,
            due_date=build_due_date(year, month, period_months_count),
            expected_amount=suggested,
        )
        created.append(payment)

    return created, skipped
