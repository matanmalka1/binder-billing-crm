from datetime import timedelta

from app.reminders.models.reminder import ReminderActionType, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time_utils import utcnow


def test_create_list_and_due_queries(test_db):
    repo = ReminderRepository(test_db)
    now = utcnow()
    due = repo.create(
        fire_at=now - timedelta(minutes=1),
        action_type=ReminderActionType.SEND_NOTIFICATION,
        source_domain="charge",
        source_id=7,
        payload={"x": 1},
    )
    future = repo.create(
        fire_at=now + timedelta(days=1),
        action_type=ReminderActionType.CREATE_TASK,
    )

    scheduled = repo.list_by_status(ReminderStatus.SCHEDULED)
    assert [item.id for item in scheduled] == [due.id, future.id]
    assert repo.count_by_status(ReminderStatus.SCHEDULED) == 2
    assert [item.id for item in repo.list_due_scheduled(now)] == [due.id]


def test_update_status_returns_none_for_missing_reminder(test_db):
    repo = ReminderRepository(test_db)

    assert repo.update_status(999999, ReminderStatus.CANCELED) is None
