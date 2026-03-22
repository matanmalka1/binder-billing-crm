from datetime import date, timedelta
from itertools import count

from app.businesses.models.business import Business, BusinessStatus, BusinessType
from app.clients.models import Client
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time_utils import utcnow


_seq = count(1)


def _client(db) -> Client:
    idx = next(_seq)
    client = Client(
        full_name=f"Reminder Repo Client {idx}",
        id_number=f"RMR{idx:03d}",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _business(db, client_id: int) -> Business:
    business = Business(
        client_id=client_id,
        business_type=BusinessType.COMPANY,
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _create_reminder(repo: ReminderRepository, business_id: int, *, send_on: date, message: str):
    return repo.create(
        business_id=business_id,
        reminder_type=ReminderType.CUSTOM,
        target_date=send_on + timedelta(days=5),
        days_before=5,
        send_on=send_on,
        message=message,
    )


def test_pending_status_and_business_queries(test_db):
    repo = ReminderRepository(test_db)
    today = date.today()
    now = utcnow()
    client_a = _client(test_db)
    client_b = _client(test_db)
    business_a = _business(test_db, client_a.id)
    business_b = _business(test_db, client_b.id)

    due_earliest = _create_reminder(repo, business_b.id, send_on=today - timedelta(days=2), message="due earliest")
    due_old = _create_reminder(repo, business_a.id, send_on=today - timedelta(days=1), message="due old")
    due_today = _create_reminder(repo, business_a.id, send_on=today, message="due today")
    future = _create_reminder(repo, business_a.id, send_on=today + timedelta(days=3), message="future")
    sent = _create_reminder(repo, business_a.id, send_on=today - timedelta(days=3), message="sent")

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

    assert repo.count_by_business(business_a.id) == 4
    by_business = repo.list_by_business(business_a.id, page=1, page_size=20)
    assert [item.id for item in by_business] == [sent.id, future.id, due_today.id, due_old.id]


def test_update_status_returns_none_for_missing_reminder(test_db):
    repo = ReminderRepository(test_db)
    assert repo.update_status(999999, ReminderStatus.CANCELED) is None


def test_reminder_repr_includes_key_fields(test_db):
    repo = ReminderRepository(test_db)
    client = _client(test_db)
    business = _business(test_db, client.id)
    reminder = _create_reminder(repo, business.id, send_on=date.today(), message="repr-check")

    text = repr(reminder)
    assert f"id={reminder.id}" in text
    assert f"business_id={business.id}" in text
