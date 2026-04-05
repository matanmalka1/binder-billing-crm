from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.businesses.models.business import BusinessType
from app.businesses.repositories.business_repository import BusinessRepository
from app.core.exceptions import NotFoundError


def generate_annual_schedule(
    business_id: int,
    year: int,
    db: Session,
    period_months_count: int = 1,
) -> tuple[list[AdvancePayment], int]:
    """
    יוצר רשומות מקדמה לעסק ולשנה נתונים.
    - period_months_count=1: 12 רשומות חודשיות (YYYY-MM)
    - period_months_count=2: 6 רשומות דו-חודשיות (YYYY-MM של חודש ראשון)
    תאריך יעד: ה-15 לחודש שאחרי התקופה.
    מדלג על תקופות שכבר קיימות (אידמפוטנטי).
    מחזיר (created_records, skipped_count).
    """
    business = BusinessRepository(db).get_by_id(business_id)
    if not business:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")

    service = AdvancePaymentService(db)
    repo = AdvancePaymentRepository(db)
    suggested: Optional[Decimal] = service.suggest_expected_amount(business_id, year, period_months_count)

    # Build list of period start months
    if period_months_count == 2:
        start_months = [1, 3, 5, 7, 9, 11]
    else:
        start_months = list(range(1, 13))

    created: list[AdvancePayment] = []
    skipped = 0

    for month in start_months:
        period = f"{year}-{month:02d}"
        if repo.exists_for_period(business_id, period):
            skipped += 1
            continue

        # Companies: due date = 15th of the period's own start month
        # Self-employed: due date = 15th of the month after the period end
        if business.business_type == BusinessType.COMPANY:
            due_month = month
            due_year = year
        else:
            due_month = month + period_months_count
            due_year = year
            if due_month > 12:
                due_month -= 12
                due_year += 1

        payment = repo.create(
            business_id=business_id,
            period=period,
            period_months_count=period_months_count,
            due_date=date(due_year, due_month, 15),
            expected_amount=suggested,
        )
        created.append(payment)

    return created, skipped