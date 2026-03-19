from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.businesses.repositories.business_repository import BusinessRepository
from app.core.exceptions import NotFoundError


def generate_annual_schedule(
    business_id: int,
    year: int,
    db: Session,
) -> tuple[list[AdvancePayment], int]:
    """
    יוצר 12 רשומות מקדמה (חודשים 1–12) לעסק ולשנה נתונים.
    תאריך יעד: ה-15 לכל חודש (סטנדרט ישראלי).
    מדלג על חודשים שכבר קיימת עבורם רשומה (אידמפוטנטי).
    מחזיר (created_records, skipped_count).
    """
    if not BusinessRepository(db).get_by_id(business_id):
        raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")

    service = AdvancePaymentService(db)
    repo = AdvancePaymentRepository(db)

    suggested: Optional[Decimal] = service.suggest_expected_amount(business_id, year)

    created: list[AdvancePayment] = []
    skipped = 0

    for month in range(1, 13):
        if repo.exists_for_month(business_id, year, month):
            skipped += 1
            continue
        payment = repo.create(
            business_id=business_id,
            year=year,
            month=month,
            due_date=date(year, month, 15),
            expected_amount=suggested,
        )
        created.append(payment)

    return created, skipped