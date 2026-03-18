from datetime import date
from types import SimpleNamespace

import pytest

from app.clients.models import Client, ClientType
from app.reminders.api import routes_create
from app.reminders.models.reminder import ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository


def _client(db) -> Client:
    crm_client = Client(
        full_name="Reminder API Additional Client",
        id_number="RMA001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def test_create_binder_idle_and_unpaid_charge_missing_ids_return_400(client, test_db, advisor_headers):
    crm_client = _client(test_db)

    idle = client.post(
        "/api/v1/reminders",
        headers=advisor_headers,
        json={
            "client_id": crm_client.id,
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
            "client_id": crm_client.id,
            "reminder_type": "unpaid_charge",
            "target_date": date.today().isoformat(),
            "days_before": 3,
        },
    )
    assert unpaid.status_code == 400


def test_mark_sent_endpoint_updates_pending_reminder(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    reminder = ReminderRepository(test_db).create(
        client_id=crm_client.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date.today(),
        days_before=0,
        send_on=date.today(),
        message="send me",
    )

    resp = client.post(f"/api/v1/reminders/{reminder.id}/mark-sent", headers=advisor_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


def test_create_tax_deadline_missing_id_returns_400(client, test_db, advisor_headers):
    crm_client = _client(test_db)
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
    assert resp.status_code == 400
    assert "tax_deadline_id" in resp.json()["detail"]


def test_create_reminder_unsupported_type_branch_direct(monkeypatch):
    class _Svc:
        def __init__(self, db):
            self.db = db

    monkeypatch.setattr(routes_create, "ReminderService", _Svc)
    request = SimpleNamespace(
        client_id=1,
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
