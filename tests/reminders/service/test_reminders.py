from datetime import date, timedelta

import pytest

from app.clients.models import Client, ClientType
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services import ReminderService
from app.core.exceptions import AppError, NotFoundError


def _client(db) -> Client:
    client = Client(
        full_name="Reminder Service Client",
        id_number="333333333",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _reminder(repo: ReminderRepository, client_id: int, *, status: ReminderStatus = ReminderStatus.PENDING):
    reminder = repo.create(
        client_id=client_id,
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
    client = _client(test_db)
    service = ReminderService(test_db)

    with pytest.raises(AppError) as exc_info:
        service.create_custom_reminder(
            client_id=client.id,
            target_date=date.today(),
            days_before=-1,
            message="Bad",
            created_by=None,
        )

    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_custom_missing_message_raises_app_error(test_db):
    client = _client(test_db)
    service = ReminderService(test_db)

    with pytest.raises(AppError) as exc_info:
        service.create_custom_reminder(
            client_id=client.id,
            target_date=date.today(),
            days_before=1,
            message="   ",
            created_by=None,
        )

    assert exc_info.value.code == "REMINDER.MESSAGE_REQUIRED"


def test_mark_sent_enforces_pending_status(test_db):
    client = _client(test_db)
    repo = ReminderRepository(test_db)
    reminder = _reminder(repo, client.id, status=ReminderStatus.SENT)

    with pytest.raises(AppError) as exc_info:
        ReminderService(test_db).mark_sent(reminder.id)

    assert exc_info.value.code == "REMINDER.INVALID_STATUS"


def test_get_pending_respects_reference_date(test_db):
    client = _client(test_db)
    repo = ReminderRepository(test_db)
    today = date.today()
    # Should be included
    repo.create(
        client_id=client.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=today,
        days_before=0,
        send_on=today,
        message="Today",
    )
    # Future send_on should be excluded
    repo.create(
        client_id=client.id,
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


def test_cancel_missing_reminder_raises_not_found(test_db):
    with pytest.raises(NotFoundError):
        ReminderService(test_db).cancel_reminder(999)


def test_mark_sent_missing_reminder_raises_not_found(test_db):
    with pytest.raises(NotFoundError):
        ReminderService(test_db).mark_sent(999999)


def test_cancel_enforces_pending_status(test_db):
    client = _client(test_db)
    repo = ReminderRepository(test_db)
    reminder = _reminder(repo, client.id, status=ReminderStatus.SENT)

    with pytest.raises(AppError) as exc_info:
        ReminderService(test_db).cancel_reminder(reminder.id)

    assert exc_info.value.code == "REMINDER.INVALID_STATUS"
