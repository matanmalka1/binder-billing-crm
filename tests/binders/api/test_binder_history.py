from datetime import date

from app.binders.models.binder import Binder, BinderCapacityStatus, BinderLocationStatus
from app.binders.repositories.binder_lifecycle_log_repository import (
    BinderLifecycleLogRepository,
)
from tests.helpers.identity import seed_client_identity


def _seed_binder_with_history(db, user_id: int):
    client = seed_client_identity(
        db,
        full_name="History Client",
        id_number="BND-HIST-1",
    )

    binder = Binder(
        client_record_id=client.id,
        binder_number="BND-H-001",
        period_start=date.today(),
        created_by=user_id,
        location_status=BinderLocationStatus.IN_OFFICE,
        capacity_status=BinderCapacityStatus.OPEN,
    )
    db.add(binder)
    db.commit()
    db.refresh(binder)

    log_repo = BinderLifecycleLogRepository(db)
    log_repo.append(
        binder.id,
        field_name="location_status",
        old_value="null",
        new_value="in_office",
        changed_by_user_id=user_id,
    )
    log_repo.append(
        binder.id,
        field_name="location_status",
        old_value="in_office",
        new_value="ready_for_handover",
        changed_by_user_id=user_id,
    )
    return binder


def test_binder_history_endpoint_returns_logs(client, test_db, advisor_headers, test_user):
    binder = _seed_binder_with_history(test_db, test_user.id)

    resp = client.get(f"/api/v1/binders/{binder.id}/history", headers=advisor_headers)
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["binder_id"] == binder.id
    history = payload["history"]
    assert len(history) == 2
    assert history[0]["old_value"] == "null"
    assert history[0]["new_value"] == "in_office"
    assert history[1]["new_value"] == "ready_for_handover"


def test_binder_history_404_when_missing(client, advisor_headers):
    resp = client.get("/api/v1/binders/9999/history", headers=advisor_headers)
    assert resp.status_code == 404
