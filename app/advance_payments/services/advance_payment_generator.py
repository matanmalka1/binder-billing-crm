from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import (
    AdvancePaymentRepository,
)
from app.advance_payments.services.constants import get_period_start_months
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.common.enums import ObligationType
from app.core.exceptions import ConflictError
from app.tax_calendar.services.materialization_service import (
    TaxCalendarMaterializationService,
)


def generate_annual_schedule(
    client_record_id: int,
    year: int,
    db: Session,
    period_months_count: Optional[int] = None,
    reference_date: Optional[date] = None,
) -> tuple[list[AdvancePayment], int]:
    """
    יוצר רשומות מקדמה ללקוח ולשנה נתונים.
    - period_months_count=1: 12 רשומות חודשיות (YYYY-MM)
    - period_months_count=2: 6 רשומות דו-חודשיות (YYYY-MM של חודש ראשון)
    תאריך יעד: מתוך רשומת יומן המס לתקופה.
    מדלג על תקופות שכבר קיימות (אידמפוטנטי).
    מדלג על תקופות שתאריך היעד שלהן לפני reference_date (ברירת מחדל: היום).
    מחזיר (created_records, skipped_count).
    """
    if reference_date is None:
        reference_date = date.today()

    service = AdvancePaymentService(db)
    service._assert_client_allows_create(client_record_id)
    configured_count = service.default_period_months_count_for_client(client_record_id)
    if period_months_count is None:
        period_months_count = configured_count
    elif period_months_count != configured_count:
        raise ConflictError(
            "תדירות המקדמות בבקשה אינה תואמת להגדרת הלקוח",
            "ADVANCE_PAYMENT.FREQUENCY_MISMATCH",
        )
    repo = AdvancePaymentRepository(db)
    tax_calendar = TaxCalendarMaterializationService(db)
    suggested: Optional[Decimal] = service.suggest_expected_amount_for_client(
        client_record_id, year, period_months_count
    )

    start_months = get_period_start_months(period_months_count)

    created: list[AdvancePayment] = []
    skipped = 0

    for month in start_months:
        period = f"{year}-{month:02d}"
        entry = tax_calendar.ensure_periodic_entry(
            ObligationType.ADVANCE_PAYMENT,
            period,
            period_months_count,
        )
        if entry.due_date < reference_date:
            skipped += 1
            continue
        if repo.exists_for_period(client_record_id, period):
            skipped += 1
            continue

        payment = service.create_payment_for_client(
            client_record_id=client_record_id,
            period=period,
            period_months_count=period_months_count,
            due_date=entry.due_date,
            expected_amount=suggested,
        )
        created.append(payment)

    return created, skipped
