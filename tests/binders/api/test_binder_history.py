from datetime import date

from app.binders.models.binder import Binder, BinderStatus
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.clients.models import Client


def _seed_binder_with_history(db, user_id: int):
    client = Client(
        full_name="History Client",
        id_number="BND-HIST-1",
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    binder = Binder(
        client_id=client.id,
        binder_number="BND-H-001",
        period_start=date.today(),
        created_by=user_id,
        status=BinderStatus.IN_OFFICE,
    )
    db.add(binder)
    db.commit()
    db.refresh(binder)

    log_repo = BinderStatusLogRepository(db)
    log_repo.append(binder.id, old_status="null", new_status="in_office", changed_by=user_id)
    log_repo.append(binder.id, old_status="in_office", new_status="ready_for_pickup", changed_by=user_id)
    return binder


def test_binder_history_endpoint_returns_logs(client, test_db, advisor_headers, test_user):
    binder = _seed_binder_with_history(test_db, test_user.id)

    resp = client.get(f"/api/v1/binders/{binder.id}/history", headers=advisor_headers)
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["binder_id"] == binder.id
    history = payload["history"]
    assert len(history) == 2
    assert history[0]["old_status"] == "null"
    assert history[0]["new_status"] == "in_office"
    assert history[1]["new_status"] == "ready_for_pickup"


def test_binder_history_404_when_missing(client, advisor_headers):
    resp = client.get("/api/v1/binders/9999/history", headers=advisor_headers)
    assert resp.status_code == 404
