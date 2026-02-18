from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.clients.repositories.client_repository import ClientRepository
from app.reminders.models.reminder import Reminder, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository


def _ensure_client_exists(client_repo: ClientRepository, client_id: int) -> None:
    if not client_repo.get_by_id(client_id):
        raise ValueError(f"Client {client_id} not found")


def create_tax_deadline_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    *,
    client_id: int,
    tax_deadline_id: int,
    target_date: date,
    days_before: int,
    message: Optional[str] = None,
) -> Reminder:
    _ensure_client_exists(client_repo, client_id)
    if days_before < 0:
        raise ValueError("days_before must be non-negative")

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
    )


def create_idle_binder_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    *,
    client_id: int,
    binder_id: int,
    days_idle: int,
    message: Optional[str] = None,
) -> Reminder:
    _ensure_client_exists(client_repo, client_id)
    if days_idle < 0:
        raise ValueError("days_idle must be non-negative")

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
    )


def create_unpaid_charge_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    *,
    client_id: int,
    charge_id: int,
    days_unpaid: int,
    message: Optional[str] = None,
) -> Reminder:
    _ensure_client_exists(client_repo, client_id)
    if days_unpaid < 0:
        raise ValueError("days_unpaid must be non-negative")

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
    )


def create_custom_reminder(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    *,
    client_id: int,
    target_date: date,
    days_before: int,
    message: str,
) -> Reminder:
    _ensure_client_exists(client_repo, client_id)
    if days_before < 0:
        raise ValueError("days_before must be non-negative")
    if not message or not message.strip():
        raise ValueError("message is required for custom reminders")

    send_on = target_date - timedelta(days=days_before)

    return reminder_repo.create(
        client_id=client_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
    )
