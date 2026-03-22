from datetime import date
from types import SimpleNamespace

import pytest

from app.binders.models.binder import Binder, BinderStatus
from app.businesses.models.business import Business, BusinessStatus, BusinessType
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models import Client
from app.reminders.api import routes_create
from app.reminders.models.reminder import ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository


def _client(db) -> Client:
    crm_client = Client(
        full_name="Reminder API Additional Client",
        id_number="RMA001",
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def _business(db, client_id: int, user_id: int) -> Business:
    business = Business(
        client_id=client_id,
        business_type=BusinessType.COMPANY,
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
        created_by=user_id,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def test_create_binder_idle_and_unpaid_charge_missing_ids_return_400(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)

    idle = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "binder_idle",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert idle.status_code == 400

    unpaid = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "unpaid_charge",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert unpaid.status_code == 400


def test_mark_sent_endpoint_updates_pending_reminder(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    reminder = ReminderRepository(test_db).create(
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="send me",
    )

    resp = client.post(f"/api/v1/reminders/{reminder.id}/mark-sent", headers=advisor_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


def test_create_tax_deadline_missing_id_returns_400(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    resp = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "tax_deadline_approaching",
            "target_date": date.today().isoformat(),
            "days_before": 2,
        },
    )
    assert resp.status_code == 400
    assert "tax_deadline_id" in resp.json()["detail"]


def test_create_reminder_unsupported_type_branch_direct(monkeypatch):
    class _Svc:
        def __init__(self, db):
            self.db = db

    monkeypatch.setattr(routes_create, "ReminderService", _Svc)
    request = SimpleNamespace(
        business_id=1,
        reminder_type="unsupported",
        target_date=date.today(),
        days_before=1,
        message="x",
        binder_id=None,
        charge_id=None,
        tax_deadline_id=None,
    )
    user = SimpleNamespace(id=1)

    with pytest.raises(Exception) as exc:
        routes_create.create_reminder(request=request, db=object(), user=user)
    assert getattr(exc.value, "status_code", None) == 400


def test_create_binder_idle_and_unpaid_charge_and_custom_success(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    binder = Binder(
        client_id=crm_client.id,
        binder_number="RMA-B",
        period_start=date.today(),
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    charge = Charge(
        business_id=business.id,
        amount=10,
        charge_type=ChargeType.ONE_TIME,
        status=ChargeStatus.ISSUED,
    )
    test_db.add_all([binder, charge])
    test_db.commit()
    test_db.refresh(binder)
    test_db.refresh(charge)

    idle = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "binder_idle",
            "target_date": date.today().isoformat(),
            "days_before": 2,
            "binder_id": binder.id,
            "message": "idle",
        },
    )
    assert idle.status_code == 201

    unpaid = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "unpaid_charge",
            "target_date": date.today().isoformat(),
            "days_before": 3,
            "charge_id": charge.id,
            "message": "unpaid",
        },
    )
    assert unpaid.status_code == 201

    custom = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "custom",
            "target_date": date.today().isoformat(),
            "days_before": 0,
            "message": "custom-ok",
        },
    )
    assert custom.status_code == 201
