from datetime import date, timedelta
from decimal import Decimal

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models import Client, ClientType
from itertools import count

from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus


_client_seq = count(1)


def _client(db) -> Client:
    client = Client(
        full_name="Reminder Client",
        id_number=f"22222222{next(_client_seq)}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _tax_deadline(db, client_id: int) -> TaxDeadline:
    deadline = TaxDeadline(
        client_id=client_id,
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
        binder_type=BinderType.VAT,
        received_at=date.today(),
        status=BinderStatus.IN_OFFICE,
        received_by=user_id,
    )
    db.add(binder)
    db.commit()
    db.refresh(binder)
    return binder


def _charge(db, client_id: int) -> Charge:
    charge = Charge(
        client_id=client_id,
        amount=Decimal("100.00"),
        currency="ILS",
        charge_type=ChargeType.ONE_TIME,
        status=ChargeStatus.ISSUED,
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def test_create_tax_deadline_reminder_success(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    deadline = _tax_deadline(test_db, crm_client.id)

    target = deadline.due_date
    response = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "client_id": crm_client.id,
            "reminder_type": "tax_deadline_approaching",
            "target_date": target.isoformat(),
            "days_before": 3,
            "tax_deadline_id": deadline.id,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["client_id"] == crm_client.id
    assert data["reminder_type"] == "tax_deadline_approaching"
    assert data["send_on"] == (target - timedelta(days=3)).isoformat()


def test_create_custom_missing_message_returns_400(client, advisor_headers):
    resp = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "client_id": 1,
            "reminder_type": "custom",
            "target_date": date.today().isoformat(),
            "days_before": 1,
        },
    )

    assert resp.status_code == 400
    assert "message" in resp.json()["detail"]


def test_cancel_reminder_marks_status_and_canceled_at(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    # create simple custom reminder directly via repo to avoid message validation duplication
    repo = ReminderRepository(test_db)
    reminder = repo.create(
        client_id=crm_client.id,
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


def test_list_reminders_filters_by_client_and_status(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    other_client = _client(test_db)

    repo = ReminderRepository(test_db)
    repo.create(
        client_id=crm_client.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="For client A",
    )
    canceled = repo.create(
        client_id=crm_client.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Canceled",
    )
    repo.update_status(canceled.id, ReminderStatus.CANCELED, canceled_at=date.today())
    repo.create(
        client_id=other_client.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="Other client",
    )

    # Client filter
    client_resp = client.get(
        f"/api/v1/reminders?client_id={crm_client.id}&page=1&page_size=10",
        headers=advisor_headers,
    )
    assert client_resp.status_code == 200
    assert all(item["client_id"] == crm_client.id for item in client_resp.json()["items"])

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
