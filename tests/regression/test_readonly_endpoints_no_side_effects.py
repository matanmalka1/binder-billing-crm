from datetime import date, timedelta

from sqlalchemy import func, select

from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_status_log import BinderStatusLog
from app.clients.models.client_record import ClientRecord


def test_readonly_get_endpoints_keep_db_state_intact(
    client, advisor_headers, test_db, test_user, create_client_with_business
):
    today = date.today()
    c, _business = create_client_with_business(
        full_name="Client D",
        id_number="444444444",
    )

    b_open = Binder(
        client_record_id=c.id,
        binder_number="BND-OPEN",
        period_start=today,
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    b_overdue = Binder(
        client_record_id=c.id,
        binder_number="BND-OVERDUE",
        period_start=today - timedelta(days=100),
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    b_due_today = Binder(
        client_record_id=c.id,
        binder_number="BND-DUE",
        period_start=today,
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
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
        "binders": test_db.scalar(select(func.count(Binder.id))),
        "logs": test_db.scalar(select(func.count(BinderStatusLog.id))),
        "clients": test_db.scalar(select(func.count(ClientRecord.id))),
        "statuses": {b.id: b.status.value for b in test_db.scalars(select(Binder)).all()},
    }

    r_client_binders = client.get(
        f"/api/v1/binders?client_record_id={c.id}", headers=advisor_headers
    )
    assert r_client_binders.status_code == 200
    assert r_client_binders.json()["total"] == 3

    r_history = client.get(f"/api/v1/binders/{b_open.id}/history", headers=advisor_headers)
    assert r_history.status_code == 200
    assert r_history.json()["binder_id"] == b_open.id

    r_overview = client.get("/api/v1/dashboard/overview", headers=advisor_headers)
    assert r_overview.status_code == 200
    assert "is_empty" in r_overview.json()
    assert "open_charges_count" in r_overview.json()

    assert test_db.scalar(select(func.count(Binder.id))) == baseline["binders"]
    assert test_db.scalar(select(func.count(BinderStatusLog.id))) == baseline["logs"]
    assert test_db.scalar(select(func.count(ClientRecord.id))) == baseline["clients"]
    assert {b.id: b.status.value for b in test_db.scalars(select(Binder)).all()} == baseline[
        "statuses"
    ]
