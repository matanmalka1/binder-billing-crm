from datetime import date

from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_intake import BinderIntake
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType


def _seed_binder_and_intakes(db, user_id: int):
    crm_client = Client(
        full_name="Binder Intake Client",
        id_number="BINT001",
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    legal = LegalEntity(id_number="LE-BINT001", id_number_type=IdNumberType.INDIVIDUAL, official_name="Test Entity")
    db.add(legal)
    db.flush()
    db.add(ClientRecord(id=crm_client.id, legal_entity_id=legal.id))
    db.flush()

    binder = Binder(
        client_id=crm_client.id,
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
