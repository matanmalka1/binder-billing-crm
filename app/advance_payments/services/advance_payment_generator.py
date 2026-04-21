from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.constants import build_due_date, get_period_start_months
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import NotFoundError


def generate_annual_schedule(
    client_record_id: int,
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
    record = ClientRecordRepository(db).get_by_id(client_record_id)
    if not record:
        raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "ADVANCE_PAYMENT.CLIENT_RECORD_NOT_FOUND")
    service = AdvancePaymentService(db)
    repo = AdvancePaymentRepository(db)
    suggested: Optional[Decimal] = service.suggest_expected_amount_for_client(
        client_record_id, year, period_months_count
    )

    start_months = get_period_start_months(period_months_count)

    created: list[AdvancePayment] = []
    skipped = 0

    for month in start_months:
        period = f"{year}-{month:02d}"
        if repo.exists_for_period(client_record_id, period):
            skipped += 1
            continue

        payment = repo.create(
            client_record_id=client_record_id,
            period=period,
            period_months_count=period_months_count,
            due_date=build_due_date(year, month, period_months_count),
            expected_amount=suggested,
        )
        created.append(payment)

    return created, skipped
