from datetime import date, timedelta

import pytest

from app.businesses.models.business import Business, BusinessStatus
from app.clients.models.client import Client
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services.reminder_service import ReminderService
from app.core.exceptions import AppError, NotFoundError
from tests.conftest import _ensure_client_identity_graph


def _client(db) -> Client:
    client = Client(
        full_name="Reminder Service Client",
        id_number="333333333",
    )
    db.add(client)
    db.flush()
    _ensure_client_identity_graph(db, client)
    db.commit()
    db.refresh(client)
    return client


def _business(db, client_id: int) -> Business:
    business = Business(
        client_id=client_id,
        business_name=f"Reminder Service Biz {client_id}",
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _reminder(repo: ReminderRepository, business_id: int, *, status: ReminderStatus = ReminderStatus.PENDING):
    business = repo.db.get(Business, business_id)
    reminder = repo.create(
        client_record_id=business.client_id,
        business_id=business_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Service Ping",
    )
    if status != ReminderStatus.PENDING:
        repo.update_status(reminder.id, status)
    return reminder


def test_custom_negative_days_raises_app_error(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    service = ReminderService(test_db)

    with pytest.raises(AppError) as exc_info:
        service.create_custom_reminder(
            business_id=business.id,
            target_date=date.today(),
            days_before=-1,
            message="Bad",
            created_by=None,
        )

    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_custom_missing_message_raises_app_error(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    service = ReminderService(test_db)

    with pytest.raises(AppError) as exc_info:
        service.create_custom_reminder(
            business_id=business.id,
            target_date=date.today(),
            days_before=1,
            message="   ",
            created_by=None,
        )

    assert exc_info.value.code == "REMINDER.MESSAGE_REQUIRED"


def test_mark_sent_enforces_pending_status(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    repo = ReminderRepository(test_db)
    reminder = _reminder(repo, business.id, status=ReminderStatus.SENT)

    with pytest.raises(AppError) as exc_info:
        ReminderService(test_db).mark_sent(reminder.id, actor_id=1)

    assert exc_info.value.code == "REMINDER.INVALID_STATUS"


def test_get_pending_respects_reference_date(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    repo = ReminderRepository(test_db)
    today = date.today()
    repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=today,
        days_before=0,
        send_on=today,
        message="Today",
    )
    repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=today + timedelta(days=5),
        days_before=0,
        send_on=today + timedelta(days=5),
        message="Future",
    )

    items, total, _ = ReminderService(test_db).get_pending_reminders(reference_date=today, page=1, page_size=10)

    assert total == 1
    assert len(items) == 1
    assert items[0].message == "Today"


def test_get_reminders_without_status_defaults_to_pending(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    repo = ReminderRepository(test_db)
    today = date.today()
    repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=today,
        days_before=0,
        send_on=today,
        message="Today Pending",
    )
    repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=today + timedelta(days=2),
        days_before=0,
        send_on=today + timedelta(days=2),
        message="Future Pending",
    )

    items, total, _ = ReminderService(test_db).get_reminders(page=1, page_size=10)

    assert total == 1
    assert len(items) == 1
    assert items[0].message == "Today Pending"


def test_cancel_missing_reminder_raises_not_found(test_db):
    with pytest.raises(NotFoundError):
        ReminderService(test_db).cancel_reminder(999, actor_id=1)


def test_mark_sent_missing_reminder_raises_not_found(test_db):
    with pytest.raises(NotFoundError):
        ReminderService(test_db).mark_sent(999999, actor_id=1)


def test_cancel_enforces_pending_status(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    repo = ReminderRepository(test_db)
    reminder = _reminder(repo, business.id, status=ReminderStatus.SENT)

    with pytest.raises(AppError) as exc_info:
        ReminderService(test_db).cancel_reminder(reminder.id, actor_id=1)

    assert exc_info.value.code == "REMINDER.INVALID_STATUS"
