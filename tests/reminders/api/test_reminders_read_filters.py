from datetime import date, timedelta
from itertools import count

from app.businesses.models.business import BusinessStatus
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from tests.helpers.identity import SeededClient, seed_business, seed_client_identity


_client_seq = count(1)


def _client(db) -> SeededClient:
    return seed_client_identity(
        db,
        full_name="Reminder Read Client",
        id_number=f"22333333{next(_client_seq)}",
    )


def _business(db, crm_client: SeededClient, user_id: int):
    business = seed_business(
        db,
        legal_entity_id=crm_client.legal_entity_id,
        business_name=f"Reminder Read Biz {crm_client.id}",
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
        created_by=user_id,
    )
    db.commit()
    db.refresh(business)
    business.client_id = crm_client.id
    return business


def test_list_reminders_filters_by_business_and_status(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    other_client = _client(test_db)
    business = _business(test_db, crm_client, test_user.id)
    other_business = _business(test_db, other_client, test_user.id)

    repo = ReminderRepository(test_db)
    repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="For business A",
    )
    canceled = repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today() + timedelta(days=1),
        days_before=0,
        send_on=date.today() + timedelta(days=1),
        message="Canceled",
    )
    repo.update_status(canceled.id, ReminderStatus.CANCELED, canceled_at=date.today())
    repo.create(
        client_record_id=other_client.id,
        business_id=other_business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Other business",
    )

    biz_resp = client.get(
        f"/api/v1/reminders?business_id={business.id}&page=1&page_size=10",
        headers=advisor_headers,
    )
    assert biz_resp.status_code == 200
    assert all(item["business_id"] == business.id for item in biz_resp.json()["items"])
    first_item = biz_resp.json()["items"][0]
    assert first_item["client_record_id"] == crm_client.id
    assert first_item["client_name"] == crm_client.full_name
    assert first_item["business_name"] is not None

    status_resp = client.get(
        "/api/v1/reminders?status=canceled&page=1&page_size=10",
        headers=advisor_headers,
    )
    assert status_resp.status_code == 200
    statuses = {item["status"] for item in status_resp.json()["items"]}
    assert statuses == {"canceled"}


def test_invalid_status_filter_returns_400(client, advisor_headers):
    resp = client.get("/api/v1/reminders?status=unknown", headers=advisor_headers)
    assert resp.status_code == 400
    assert resp.json()["error"] == "REMINDER.INVALID_STATUS"


def test_ready_due_filter_returns_only_due_pending(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client, test_user.id)
    repo = ReminderRepository(test_db)
    due = repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Due now",
    )
    repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today() + timedelta(days=7),
        days_before=0,
        send_on=date.today() + timedelta(days=7),
        message="Future",
    )

    resp = client.get(
        "/api/v1/reminders?status=pending&due=ready&page=1&page_size=10",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    assert [item["id"] for item in resp.json()["items"]] == [due.id]


def test_get_reminder_not_found_returns_404(client, advisor_headers):
    resp = client.get("/api/v1/reminders/999", headers=advisor_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "התזכורת לא נמצאה"


def test_get_reminder_success_returns_200(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client, test_user.id)
    reminder = ReminderRepository(test_db).create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="hello",
    )

    resp = client.get(f"/api/v1/reminders/{reminder.id}", headers=advisor_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == reminder.id
