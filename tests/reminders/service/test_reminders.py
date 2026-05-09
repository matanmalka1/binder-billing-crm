from datetime import timedelta

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.reminders.models.reminder import ReminderActionType, ReminderStatus
from app.reminders.schemas.reminders import ReminderCreateRequest
from app.reminders.services.reminder_executor_service import ReminderExecutorService
from app.reminders.services.reminder_service import ReminderService
from app.utils.time_utils import utcnow


def test_create_scheduled_reminder_from_request(test_db):
    now = utcnow()
    reminder = ReminderService(test_db).create_from_request(
        ReminderCreateRequest(
            fire_at=now,
            action_type=ReminderActionType.SEND_NOTIFICATION,
            source_domain="charge",
            source_id=12,
            notification_template_key="charge_due",
            payload={"charge_id": 12},
        ),
        created_by_user_id=5,
    )

    assert reminder.status == ReminderStatus.SCHEDULED
    assert reminder.created_by_user_id == 5
    assert reminder.payload == {"charge_id": 12}


def test_cancel_only_scheduled_reminders(test_db):
    service = ReminderService(test_db)
    reminder = service.create_from_request(
        ReminderCreateRequest(
            fire_at=utcnow(),
            action_type=ReminderActionType.CREATE_TASK,
        ),
        created_by_user_id=1,
    )

    canceled = service.cancel_reminder(reminder.id)
    assert canceled.status == ReminderStatus.CANCELED
    with pytest.raises(AppError):
        service.cancel_reminder(reminder.id)


def test_cancel_failed_reminder_rejected(test_db):
    service = ReminderService(test_db)
    reminder = service.create_from_request(
        ReminderCreateRequest(
            fire_at=utcnow(),
            action_type=ReminderActionType.CREATE_TASK,
        ),
        created_by_user_id=1,
    )
    service.reminder_repo.update_status(reminder.id, ReminderStatus.FAILED)

    with pytest.raises(AppError):
        service.cancel_reminder(reminder.id)


def test_cancel_fired_reminder_rejected(test_db):
    service = ReminderService(test_db)
    reminder = service.create_from_request(
        ReminderCreateRequest(
            fire_at=utcnow(),
            action_type=ReminderActionType.SEND_NOTIFICATION,
        ),
        created_by_user_id=1,
    )
    service.reminder_repo.update_status(reminder.id, ReminderStatus.FIRED)

    with pytest.raises(AppError):
        service.cancel_reminder(reminder.id)


def test_cancel_missing_reminder_raises_not_found(test_db):
    with pytest.raises(NotFoundError):
        ReminderService(test_db).cancel_reminder(999999)


def test_fire_due_ignores_future_and_terminal_reminders(test_db):
    now = utcnow()
    repo = ReminderService(test_db).reminder_repo
    due = repo.create(
        fire_at=now - timedelta(minutes=1),
        action_type=ReminderActionType.CREATE_TASK,
    )
    repo.create(
        fire_at=now + timedelta(days=1),
        action_type=ReminderActionType.CREATE_TASK,
    )
    canceled = repo.create(
        fire_at=now - timedelta(days=1),
        action_type=ReminderActionType.SEND_NOTIFICATION,
    )
    repo.update_status(canceled.id, ReminderStatus.CANCELED)

    result = ReminderExecutorService(test_db).fire_due(now=now)

    assert result.processed == 1
    assert result.fired == 0
    assert result.failed == 1
    assert repo.get_by_id(due.id).status == ReminderStatus.FAILED


def test_fire_due_is_idempotent_for_failed_reminders(test_db):
    now = utcnow()
    repo = ReminderService(test_db).reminder_repo
    reminder = repo.create(
        fire_at=now - timedelta(minutes=1),
        action_type=ReminderActionType.CREATE_TASK_AND_NOTIFY,
    )

    first = ReminderExecutorService(test_db).fire_due(now=now)
    second = ReminderExecutorService(test_db).fire_due(now=now)

    assert first.processed == 1
    assert second.processed == 0
    assert "עדיין לא ממומש" in repo.get_by_id(reminder.id).failure_reason


def test_send_notification_failure_reason_is_not_delivery_failure(test_db):
    now = utcnow()
    repo = ReminderService(test_db).reminder_repo
    reminder = repo.create(
        fire_at=now - timedelta(minutes=1),
        action_type=ReminderActionType.SEND_NOTIFICATION,
    )

    ReminderExecutorService(test_db).fire_due(now=now)

    reason = repo.get_by_id(reminder.id).failure_reason
    assert "עדיין לא ממומש" in reason
    assert "delivery" not in reason.lower()
    assert "שליחה נכשלה" not in reason
