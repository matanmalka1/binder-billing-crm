from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.binders.repositories.binder_repository import BinderRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_lookup import get_client_or_raise
from app.reminders.models.reminder import Reminder, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


def create_tax_deadline_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    tax_deadline_repo: TaxDeadlineRepository,
    *,
    client_id: int,
    tax_deadline_id: int,
    target_date: date,
    days_before: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    get_client_or_raise(client_repo, client_id)
    if not tax_deadline_repo.get_by_id(tax_deadline_id):
        raise ValueError(f"מועד מס {tax_deadline_id} לא נמצא")
    if days_before < 0:
        raise ValueError("המספר המייצג כמה ימים לפני חייב להיות מספר לא שלילי")

    send_on = target_date - timedelta(days=days_before)
    if message is None:
        message = f"תזכורת: מועד מס בעוד {days_before} ימים ({target_date})"

    return reminder_repo.create(
        client_id=client_id,
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
    client_repo: ClientRepository,
    binder_repo: BinderRepository,
    *,
    client_id: int,
    binder_id: int,
    days_idle: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    get_client_or_raise(client_repo, client_id)
    if not binder_repo.get_by_id(binder_id):
        raise ValueError(f"תיק {binder_id} לא נמצא")
    if days_idle < 0:
        raise ValueError("המספר המייצג כמה ימים מאז שטיפול הפסיק חייב להיות מספר לא שלילי")

    target_date = date.today() + timedelta(days=days_idle)
    send_on = date.today()
    if message is None:
        message = f"תזכורת: תיק לא טופל {days_idle} ימים"

    return reminder_repo.create(
        client_id=client_id,
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
    client_repo: ClientRepository,
    charge_repo: ChargeRepository,
    *,
    client_id: int,
    charge_id: int,
    days_unpaid: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    get_client_or_raise(client_repo, client_id)
    if not charge_repo.get_by_id(charge_id):
        raise ValueError(f"חיוב {charge_id} לא נמצא")
    if days_unpaid < 0:
        raise ValueError("המספר המייצג כמה ימים מאז שלא שולם החיוב חייב להיות מספר לא שלילי")

    target_date = date.today()
    send_on = date.today()
    if message is None:
        message = f"תזכורת: חשבונית לא שולמה {days_unpaid} ימים"

    return reminder_repo.create(
        client_id=client_id,
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
    client_repo: ClientRepository,
    *,
    client_id: int,
    target_date: date,
    days_before: int,
    message: str,
    created_by: Optional[int] = None,
) -> Reminder:
    get_client_or_raise(client_repo, client_id)
    if days_before < 0:
        raise ValueError("המספר המייצג כמה ימים לפני חייב להיות מספר לא שלילי")
    if not message or not message.strip():
        raise ValueError("נדרש טקסט עבור תזכורות מותאמות אישית")

    send_on = target_date - timedelta(days=days_before)

    return reminder_repo.create(
        client_id=client_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
        created_by=created_by,
    )
