from datetime import date

from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_intake import BinderIntake
from tests.helpers.identity import seed_client_identity


def _seed_binder_and_intakes(db, user_id: int):
    crm_client = seed_client_identity(
        db,
        full_name="Binder Intake Client",
        id_number="BINT001",
    )

    binder = Binder(
        client_record_id=crm_client.id,
        binder_number="BIN-1",
        period_start=date.today(),
        created_by=user_id,
        status=BinderStatus.IN_OFFICE,
    )
    db.add(binder)
    db.commit()
    db.refresh(binder)

    intake = BinderIntake(
        binder_id=binder.id,
        received_by=user_id,
        received_at=date.today(),
        notes="docs",
    )
    db.add(intake)
    db.commit()

    return binder


def test_binder_intakes_endpoint_success_and_not_found(client, test_db, advisor_headers, test_user):
    binder = _seed_binder_and_intakes(test_db, test_user.id)

    ok = client.get(f"/api/v1/binders/{binder.id}/intakes", headers=advisor_headers)
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["binder_id"] == binder.id
    assert len(payload["intakes"]) == 1
    assert payload["intakes"][0]["received_by_name"] == test_user.full_name

    missing = client.get("/api/v1/binders/999999/intakes", headers=advisor_headers)
    assert missing.status_code == 404
