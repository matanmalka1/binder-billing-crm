from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.binders.repositories.binder_repository import BinderRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


def create_tax_deadline_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: TaxDeadlineRepository,
    *,
    business_id: int,
    tax_deadline_id: int,
    target_date: date,
    days_before: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    get_business_or_raise(business_repo.db, business_id)
    if not tax_deadline_repo.get_by_id(tax_deadline_id):
        raise NotFoundError(f"מועד מס {tax_deadline_id} לא נמצא", "REMINDER.NOT_FOUND")
    if days_before < 0:
        raise AppError("המספר המייצג כמה ימים לפני חייב להיות מספר לא שלילי", "REMINDER.NEGATIVE_DAYS")

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = f"תזכורת: מועד מס בעוד {days_before} ימים ({target_date})"

    return reminder_repo.create(
        business_id=business_id,
        reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message,
        tax_deadline_id=tax_deadline_id,
        created_by=created_by,
    )


def create_idle_binder_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    binder_repo: BinderRepository,
    *,
    business_id: int,
    binder_id: int,
    days_idle: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    get_business_or_raise(business_repo.db, business_id)
    if not binder_repo.get_by_id(binder_id):
        raise NotFoundError(f"תיק {binder_id} לא נמצא", "REMINDER.NOT_FOUND")
    if days_idle < 0:
        raise AppError(
            "המספר המייצג כמה ימים מאז שטיפול הפסיק חייב להיות מספר לא שלילי",
            "REMINDER.NEGATIVE_DAYS",
        )

    target_date = date.today() + timedelta(days=days_idle)
    send_on = date.today()
    if message is None:
        message = f"תזכורת: תיק לא טופל {days_idle} ימים"

    return reminder_repo.create(
        business_id=business_id,
        reminder_type=ReminderType.BINDER_IDLE,
        target_date=target_date,
        days_before=0,
        send_on=send_on,
        message=message,
        binder_id=binder_id,
        created_by=created_by,
    )


def create_unpaid_charge_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    charge_repo: ChargeRepository,
    *,
    business_id: int,
    charge_id: int,
    days_unpaid: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    get_business_or_raise(business_repo.db, business_id)
    if not charge_repo.get_by_id(charge_id):
        raise NotFoundError(f"חיוב {charge_id} לא נמצא", "REMINDER.NOT_FOUND")
    if days_unpaid < 0:
        raise AppError(
            "המספר המייצג כמה ימים מאז שלא שולם החיוב חייב להיות מספר לא שלילי",
            "REMINDER.NEGATIVE_DAYS",
        )

    target_date = date.today()
    send_on = date.today()
    if message is None:
        message = f"תזכורת: חשבונית לא שולמה {days_unpaid} ימים"

    return reminder_repo.create(
        business_id=business_id,
        reminder_type=ReminderType.UNPAID_CHARGE,
        target_date=target_date,
        days_before=0,
        send_on=send_on,
        message=message,
        charge_id=charge_id,
        created_by=created_by,
    )


def create_custom_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    business_id: int,
    target_date: date,
    days_before: int,
    message: str,
    created_by: Optional[int] = None,
) -> Reminder:
    get_business_or_raise(business_repo.db, business_id)
    if days_before < 0:
        raise AppError("המספר המייצג כמה ימים לפני חייב להיות מספר לא שלילי", "REMINDER.NEGATIVE_DAYS")
    if not message or not message.strip():
        raise AppError("נדרש טקסט עבור תזכורות מותאמות אישית", "REMINDER.MESSAGE_REQUIRED")

    send_on = target_date - timedelta(days=days_before)

    return reminder_repo.create(
        business_id=business_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
        created_by=created_by,
    )
