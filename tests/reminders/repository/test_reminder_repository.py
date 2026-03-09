from datetime import date, timedelta
from itertools import count

from app.clients.models import Client, ClientType
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time_utils import utcnow


_client_seq = count(1)


def _client(db) -> Client:
    idx = next(_client_seq)
    client = Client(
        full_name=f"Reminder Repo Client {idx}",
        id_number=f"RMR{idx:03d}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _create_reminder(repo: ReminderRepository, client_id: int, *, send_on: date, message: str):
    return repo.create(
        client_id=client_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=send_on + timedelta(days=5),
        days_before=5,
        send_on=send_on,
        message=message,
    )


def test_pending_status_and_client_queries(test_db):
    repo = ReminderRepository(test_db)
    today = date.today()
    now = utcnow()
    client_a = _client(test_db)
    client_b = _client(test_db)

    due_earliest = _create_reminder(repo, client_b.id, send_on=today - timedelta(days=2), message="due earliest")
    due_old = _create_reminder(repo, client_a.id, send_on=today - timedelta(days=1), message="due old")
    due_today = _create_reminder(repo, client_a.id, send_on=today, message="due today")
    future = _create_reminder(repo, client_a.id, send_on=today + timedelta(days=3), message="future")
    sent = _create_reminder(repo, client_a.id, send_on=today - timedelta(days=3), message="sent")

    repo.update_status(sent.id, ReminderStatus.SENT, sent_at=now)

    due_old.created_at = now - timedelta(minutes=4)
    due_today.created_at = now - timedelta(minutes=3)
    future.created_at = now - timedelta(minutes=2)
    sent.created_at = now - timedelta(minutes=1)
    test_db.commit()

    pending = repo.list_pending_by_date(reference_date=today, page=1, page_size=20)
    assert [item.id for item in pending] == [due_earliest.id, due_old.id, due_today.id]
    assert repo.count_pending_by_date(reference_date=today) == 3

    sent_list = repo.list_by_status(status=ReminderStatus.SENT, page=1, page_size=20)
    assert [item.id for item in sent_list] == [sent.id]
    assert repo.count_by_status(ReminderStatus.SENT) == 1

    assert repo.count_by_client(client_a.id) == 4
    by_client = repo.list_by_client(client_a.id, page=1, page_size=20)
    assert [item.id for item in by_client] == [sent.id, future.id, due_today.id, due_old.id]


def test_update_status_returns_none_for_missing_reminder(test_db):
    repo = ReminderRepository(test_db)
    assert repo.update_status(999999, ReminderStatus.CANCELED) is None

