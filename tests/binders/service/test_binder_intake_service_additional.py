from datetime import date

import pytest

from app.binders.models.binder import Binder, BinderStatus
from app.binders.services.binder_intake_service import BinderIntakeService
from app.clients.models import Client
from app.core.exceptions import ConflictError


def _client(db, id_number: str) -> Client:
    client = Client(
        full_name=f"Binder Intake {id_number}",
        id_number=id_number,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_receive_raises_conflict_when_binder_belongs_to_other_client(test_db, test_user):
    owner = _client(test_db, "BI-SVC-001")
    other = _client(test_db, "BI-SVC-002")

    existing = Binder(
        client_id=owner.id,
        binder_number="BIN-CONFLICT-1",
        period_start=date.today(),
        created_by=test_user.id,
        status=BinderStatus.IN_OFFICE,
    )
    test_db.add(existing)
    test_db.commit()

    service = BinderIntakeService(test_db)
    with pytest.raises(ConflictError) as exc_info:
        service.receive(
            client_id=other.id,
            binder_number="BIN-CONFLICT-1",
            period_start=date.today(),
            received_at=date.today(),
            received_by=test_user.id,
            notes="should fail",
        )

    assert exc_info.value.code == "BINDER.CLIENT_MISMATCH"


def test_receive_reuses_existing_binder_for_same_client(test_db, test_user):
    client = _client(test_db, "BI-SVC-003")
    existing = Binder(
        client_id=client.id,
        binder_number="BIN-EXISTING-1",
        period_start=date.today(),
        created_by=test_user.id,
        status=BinderStatus.IN_OFFICE,
    )
    test_db.add(existing)
    test_db.commit()
    test_db.refresh(existing)

    service = BinderIntakeService(test_db)
    binder, intake, is_new = service.receive(
        client_id=client.id,
        binder_number="BIN-EXISTING-1",
        period_start=date.today(),
        received_at=date.today(),
        received_by=test_user.id,
        notes="existing binder path",
    )

    assert binder.id == existing.id
    assert intake.binder_id == existing.id
    assert is_new is False
