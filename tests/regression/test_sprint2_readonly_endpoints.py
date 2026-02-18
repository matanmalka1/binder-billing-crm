from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_status_log import BinderStatusLog
from app.clients.models.client import Client, ClientType


def test_sprint2_get_endpoints_do_not_mutate_state(client, advisor_headers, test_db, test_user):
    today = date.today()
    c = Client(
        full_name="Client D",
        id_number="444444444",
        client_type=ClientType.OSEK_PATUR,
        opened_at=today,
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)

    b_open = Binder(
        client_id=c.id,
        binder_number="BND-OPEN",
        received_at=today,
        expected_return_at=today + timedelta(days=1),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    b_overdue = Binder(
        client_id=c.id,
        binder_number="BND-OVERDUE",
        received_at=today - timedelta(days=100),
        expected_return_at=today - timedelta(days=1),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    b_due_today = Binder(
        client_id=c.id,
        binder_number="BND-DUE",
        received_at=today,
        expected_return_at=today,
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    test_db.add_all([b_open, b_overdue, b_due_today])
    test_db.commit()

    test_db.refresh(b_open)
    log = BinderStatusLog(
        binder_id=b_open.id,
        old_status="null",
        new_status="in_office",
        changed_by=test_user.id,
        notes="seed",
    )
    test_db.add(log)
    test_db.commit()

    baseline = {
        "binders": test_db.query(Binder).count(),
        "logs": test_db.query(BinderStatusLog).count(),
        "clients": test_db.query(Client).count(),
        "statuses": {b.id: b.status.value for b in test_db.query(Binder).all()},
    }

    r_client_binders = client.get(f"/api/v1/clients/{c.id}/binders", headers=advisor_headers)
    assert r_client_binders.status_code == 200
    assert r_client_binders.json()["total"] == 3

    r_history = client.get(f"/api/v1/binders/{b_open.id}/history", headers=advisor_headers)
    assert r_history.status_code == 200
    assert r_history.json()["binder_id"] == b_open.id

    r_summary = client.get("/api/v1/dashboard/summary", headers=advisor_headers)
    assert r_summary.status_code == 200
    assert "binders_in_office" in r_summary.json()

    r_overview = client.get("/api/v1/dashboard/overview", headers=advisor_headers)
    assert r_overview.status_code == 200
    assert "total_clients" in r_overview.json()

    assert test_db.query(Binder).count() == baseline["binders"]
    assert test_db.query(BinderStatusLog).count() == baseline["logs"]
    assert test_db.query(Client).count() == baseline["clients"]
    assert {b.id: b.status.value for b in test_db.query(Binder).all()} == baseline["statuses"]
