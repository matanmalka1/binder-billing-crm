from datetime import date, timedelta
from decimal import Decimal
from itertools import count

from app.binders.models.binder import Binder, BinderStatus
from app.businesses.models.business import Business, BusinessStatus, EntityType
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models.client import Client
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus


_client_seq = count(1)


def _client(db) -> Client:
    client = Client(
        full_name="Reminder Client",
        id_number=f"22222222{next(_client_seq)}",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _business(db, client_id: int, user_id: int) -> Business:
    business = Business(
        client_id=client_id,
        entity_type=EntityType.COMPANY_LTD,
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
        created_by=user_id,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _tax_deadline(db, business_id: int) -> TaxDeadline:
    deadline = TaxDeadline(
        business_id=business_id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
        status=TaxDeadlineStatus.PENDING,
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def _binder(db, client_id: int, user_id: int) -> Binder:
    binder = Binder(
        client_id=client_id,
        binder_number="B-1",
        period_start=date.today(),
        status=BinderStatus.IN_OFFICE,
        created_by=user_id,
    )
    db.add(binder)
    db.commit()
    db.refresh(binder)
    return binder


def _charge(db, business_id: int) -> Charge:
    charge = Charge(
        business_id=business_id,
        amount=Decimal("100.00"),
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def test_create_tax_deadline_reminder_success(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    deadline = _tax_deadline(test_db, business.id)

    target = deadline.due_date
    response = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "tax_deadline_approaching",
            "target_date": target.isoformat(),
            "days_before": 3,
            "tax_deadline_id": deadline.id,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["business_id"] == business.id
    assert data["reminder_type"] == "tax_deadline_approaching"
    assert data["send_on"] == (target - timedelta(days=3)).isoformat()


def test_create_custom_missing_message_returns_422(client, advisor_headers):
    resp = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": 1,
            "reminder_type": "custom",
            "target_date": date.today().isoformat(),
            "days_before": 1,
        },
    )

    assert resp.status_code == 422
    assert any("message" in err["msg"] for err in resp.json()["detail"])


def test_cancel_reminder_marks_status_and_canceled_at(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    repo = ReminderRepository(test_db)
    reminder = repo.create(
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Ping",
    )

    resp = client.post(f"/api/v1/reminders/{reminder.id}/cancel", headers=advisor_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "canceled"
    assert body["canceled_at"] is not None

    updated = repo.get_by_id(reminder.id)
    assert updated.status == ReminderStatus.CANCELED


def test_list_reminders_filters_by_business_and_status(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    other_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    other_business = _business(test_db, other_client.id, test_user.id)

    repo = ReminderRepository(test_db)
    repo.create(
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="For business A",
    )
    canceled = repo.create(
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Canceled",
    )
    repo.update_status(canceled.id, ReminderStatus.CANCELED, canceled_at=date.today())
    repo.create(
        business_id=other_business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Other business",
    )

    # Business filter
    biz_resp = client.get(
        f"/api/v1/reminders?business_id={business.id}&page=1&page_size=10",
        headers=advisor_headers,
    )
    assert biz_resp.status_code == 200
    assert all(item["business_id"] == business.id for item in biz_resp.json()["items"])
    first_item = biz_resp.json()["items"][0]
    assert first_item["client_id"] == crm_client.id
    assert first_item["client_name"] == crm_client.full_name
    assert first_item["business_name"] is not None

    # Status filter
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


def test_get_reminder_not_found_returns_404(client, advisor_headers):
    resp = client.get("/api/v1/reminders/999", headers=advisor_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "התזכורת לא נמצאה"


def test_get_reminder_success_returns_200(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    reminder = ReminderRepository(test_db).create(
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
