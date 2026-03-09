from datetime import date, timedelta
from itertools import count

import pytest

from app.clients.models import Client, ClientType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


_client_seq = count(1)


def _client(db) -> Client:
    c = Client(
        full_name=f"Tax Deadline Client {next(_client_seq)}",
        id_number=f"12121212{next(_client_seq)}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_create_and_get_tax_deadline(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    due = date.today() + timedelta(days=10)

    create = client.post(
        "/api/v1/tax-deadlines",
        headers=advisor_headers,
        json={
            "client_id": crm_client.id,
            "deadline_type": "vat",
            "due_date": due.isoformat(),
            "payment_amount": 1500.5,
            "description": "VAT filing",
        },
    )
    assert create.status_code == 201
    payload = create.json()
    deadline_id = payload["id"]
    assert payload["deadline_type"] == "vat"
    assert payload["status"] == "pending"

    fetched = client.get(f"/api/v1/tax-deadlines/{deadline_id}", headers=advisor_headers)
    assert fetched.status_code == 200
    assert fetched.json()["payment_amount"] == 1500.5


def test_complete_updates_status_and_completed_at(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = TaxDeadlineRepository(test_db)
    deadline = repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=3),
    )

    resp = client.post(f"/api/v1/tax-deadlines/{deadline.id}/complete", headers=advisor_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None


def test_update_deadline_fields(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = TaxDeadlineRepository(test_db)
    deadline = repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=5),
        payment_amount=100.0,
        description="Old desc",
    )

    resp = client.put(
        f"/api/v1/tax-deadlines/{deadline.id}",
        headers=advisor_headers,
        json={"deadline_type": "annual_report", "payment_amount": 200.5, "description": "Updated"},
    )

    assert resp.status_code == 200
    updated = resp.json()
    assert updated["deadline_type"] == "annual_report"
    assert updated["payment_amount"] == 200.5
    assert updated["description"] == "Updated"


def test_delete_deadline_removes_record(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = TaxDeadlineRepository(test_db)
    deadline = repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=1),
    )

    resp = client.delete(f"/api/v1/tax-deadlines/{deadline.id}", headers=advisor_headers)
    assert resp.status_code == 204
    assert repo.get_by_id(deadline.id) is None


def test_list_deadlines_filters_by_client_and_type(client, test_db, advisor_headers):
    client_a = _client(test_db)
    client_b = _client(test_db)
    repo = TaxDeadlineRepository(test_db)
    repo.create(client_id=client_a.id, deadline_type=DeadlineType.VAT, due_date=date.today() + timedelta(days=2))
    repo.create(client_id=client_a.id, deadline_type=DeadlineType.ADVANCE_PAYMENT, due_date=date.today() + timedelta(days=5))
    repo.create(client_id=client_b.id, deadline_type=DeadlineType.VAT, due_date=date.today() + timedelta(days=2))

    resp = client.get(
        f"/api/v1/tax-deadlines?client_id={client_a.id}&deadline_type=vat",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["client_id"] == client_a.id
    assert items[0]["deadline_type"] == "vat"


def test_dashboard_urgent_includes_overdue_and_yellow(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = TaxDeadlineRepository(test_db)
    # Overdue
    repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() - timedelta(days=1),
    )
    # Red (due in 2 days)
    repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date.today() + timedelta(days=2),
    )
    # Yellow (due in 5 days)
    repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=date.today() + timedelta(days=5),
    )
    # Green (should not appear in urgent list)
    repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.NATIONAL_INSURANCE,
        due_date=date.today() + timedelta(days=30),
    )

    resp = client.get("/api/v1/tax-deadlines/dashboard/urgent", headers=advisor_headers)
    assert resp.status_code == 200
    data = resp.json()
    urgent_types = {item["deadline_type"] for item in data["urgent"]}
    assert urgent_types == {"vat", "advance_payment", "annual_report"}
    # Upcoming covers next 7 days (red+yellow), excludes green 30-day item
    upcoming_types = {item["deadline_type"] for item in data["upcoming"]}
    assert upcoming_types == {"advance_payment", "annual_report"}


def test_update_without_fields_returns_400(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = TaxDeadlineRepository(test_db)
    deadline = repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
    )

    resp = client.put(f"/api/v1/tax-deadlines/{deadline.id}", headers=advisor_headers, json={})
    assert resp.status_code == 400
    assert resp.json()["error"] == "TAX_DEADLINE.NO_FIELDS_PROVIDED"
