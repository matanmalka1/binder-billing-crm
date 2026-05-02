from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_guards import get_business_or_raise
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.guards.client_record_guards import assert_client_record_is_active
from app.core.exceptions import AppError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services.messages import (
    BINDER_NOT_FOUND,
    CUSTOM_REMINDER_MESSAGE_REQUIRED,
    DOCUMENT_MISSING_MESSAGE_REQUIRED,
    IDLE_BINDER_REMINDER_DEFAULT,
    NEGATIVE_DAYS,
)


def _require_non_negative_days(days_before: int) -> None:
    if days_before < 0:
        raise AppError(NEGATIVE_DAYS, "REMINDER.NEGATIVE_DAYS")


def _resolve_client_record_id(client_record_id: int, repo: ClientRecordRepository) -> int:
    client_record = repo.get_by_id(client_record_id)
    assert_client_record_is_active(client_record)
    return client_record.id


def _resolve_business_client_record_id(business, repo: ClientRecordRepository) -> int:
    client_record = repo.get_by_legal_entity_id(business.legal_entity_id)
    assert_client_record_is_active(client_record)
    return client_record.id


def create_idle_binder_reminder(
    reminder_repo: ReminderRepository,
    binder_repo: BinderRepository,
    *,
    binder_id: int,
    days_idle: int,
    message: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Reminder:
    binder = binder_repo.get_by_id(binder_id)
    if not binder:
        raise NotFoundError(BINDER_NOT_FOUND.format(binder_id=binder_id), "REMINDER.NOT_FOUND")
    _require_non_negative_days(days_idle)
    target_date = date.today() + timedelta(days=days_idle)
    send_on = date.today()
    if message is None:
        message = IDLE_BINDER_REMINDER_DEFAULT.format(days_idle=days_idle)
    return reminder_repo.create(
        client_record_id=binder.client_record_id,
        reminder_type=ReminderType.BINDER_IDLE,
        target_date=target_date,
        days_before=0,
        send_on=send_on,
        message=message,
        binder_id=binder_id,
        created_by=created_by,
    )


def create_document_missing_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    business_id: int,
    target_date: date,
    days_before: int,
    message: str,
    created_by: Optional[int] = None,
) -> Reminder:
    business = get_business_or_raise(business_repo.db, business_id)
    _require_non_negative_days(days_before)
    if not message or not message.strip():
        raise AppError(DOCUMENT_MISSING_MESSAGE_REQUIRED, "REMINDER.MESSAGE_REQUIRED")
    send_on = target_date - timedelta(days=days_before)
    client_record_id = _resolve_business_client_record_id(business, ClientRecordRepository(reminder_repo.db))
    return reminder_repo.create(
        client_record_id=client_record_id,
        business_id=business_id,
        reminder_type=ReminderType.DOCUMENT_MISSING,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
        created_by=created_by,
    )


def create_custom_reminder(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    client_record_id: Optional[int] = None,
    business_id: Optional[int] = None,
    target_date: date,
    days_before: int,
    message: str,
    created_by: Optional[int] = None,
) -> Reminder:
    if business_id is not None:
        business = get_business_or_raise(business_repo.db, business_id)
        resolved_client_record_id = _resolve_business_client_record_id(
            business, ClientRecordRepository(reminder_repo.db)
        )
        if client_record_id is not None and client_record_id != resolved_client_record_id:
            raise AppError("business_id אינו שייך ל-client_record_id שסופק", "REMINDER.BUSINESS_CLIENT_MISMATCH")
    elif client_record_id is not None:
        resolved_client_record_id = client_record_id
    else:
        raise AppError("client_record_id או business_id נדרש עבור תזכורת מותאמת אישית", "REMINDER.MISSING_ANCHOR")
    _require_non_negative_days(days_before)
    if not message or not message.strip():
        raise AppError(CUSTOM_REMINDER_MESSAGE_REQUIRED, "REMINDER.MESSAGE_REQUIRED")
    send_on = target_date - timedelta(days=days_before)
    client_record_id = _resolve_client_record_id(resolved_client_record_id, ClientRecordRepository(reminder_repo.db))
    return reminder_repo.create(
        client_record_id=client_record_id,
        business_id=business_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target_date,
        days_before=days_before,
        send_on=send_on,
        message=message.strip(),
        created_by=created_by,
    )
