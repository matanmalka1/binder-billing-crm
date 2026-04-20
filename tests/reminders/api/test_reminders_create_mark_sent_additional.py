from datetime import date

import pytest

from app.binders.models.binder import Binder, BinderStatus
from app.businesses.models.business import Business, BusinessStatus
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models.client import Client
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from tests.conftest import _ensure_client_identity_graph


def _client(db) -> Client:
    crm_client = Client(
        full_name="Reminder API Additional Client",
        id_number="RMA001",
    )
    db.add(crm_client)
    db.flush()
    _ensure_client_identity_graph(db, crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def _business(db, client_id: int, user_id: int) -> Business:
    business = Business(
        client_id=client_id,
        business_name=f"Reminder API Biz {client_id}",
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
    assert idle.status_code == 422

    unpaid = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "client_id": crm_client.id,
            "reminder_type": "unpaid_charge",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert unpaid.status_code == 422


def test_mark_sent_endpoint_updates_pending_reminder(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    reminder = ReminderRepository(test_db).create(
        client_record_id=crm_client.id,
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


def test_create_tax_deadline_missing_id_returns_422(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    resp = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "client_id": crm_client.id,
            "reminder_type": "tax_deadline_approaching",
            "target_date": date.today().isoformat(),
            "days_before": 2,
        },
    )
    assert resp.status_code == 422
    assert any("tax_deadline_id" in err["msg"] for err in resp.json()["detail"])


def test_create_binder_idle_and_unpaid_charge_and_custom_success(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)
    binder = Binder(
        client_record_id=crm_client.id,
        binder_number="RMA-B",
        period_start=date.today(),
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    charge = Charge(
        client_record_id=crm_client.id,
        business_id=business.id,
        amount=10,
        charge_type=ChargeType.OTHER,
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
            "client_id": crm_client.id,
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


def test_create_annual_report_and_advance_payment_missing_ids_return_422(client, test_db, advisor_headers, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id, test_user.id)

    annual = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "annual_report_deadline",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert annual.status_code == 422
    assert any("annual_report_id" in err["msg"] for err in annual.json()["detail"])

    advance = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "reminder_type": "advance_payment_due",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert advance.status_code == 422
    assert any("advance_payment_id" in err["msg"] for err in advance.json()["detail"])
