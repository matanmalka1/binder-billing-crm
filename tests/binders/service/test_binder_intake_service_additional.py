from datetime import date

import pytest

from app.binders.models.binder import Binder, BinderStatus
from app.binders.services.binder_intake_service import BinderIntakeService
from app.businesses.models.business import Business, BusinessStatus, EntityType
from app.clients.models.client import Client
from app.core.exceptions import AppError


def _client(db, id_number: str) -> Client:
    client = Client(
        full_name=f"Binder Intake {id_number}",
        id_number=id_number,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _business(db, client_id: int, status: BusinessStatus = BusinessStatus.ACTIVE) -> Business:
    biz = Business(
        client_id=client_id,
        entity_type=EntityType.OSEK_PATUR,
        status=status,
        opened_at=date.today(),
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)
    return biz


def test_receive_creates_composite_binder_label(test_db, test_user):
    client = _client(test_db, "BI-SVC-NEW-001")
    _business(test_db, client.id)

    service = BinderIntakeService(test_db)
    binder, _, is_new = service.receive(
        client_id=client.id,
        period_start=date.today(),
        received_at=date.today(),
        received_by=test_user.id,
    )

    assert is_new is True
    assert binder.binder_number == f"{client.id}/1"


def test_receive_reuses_existing_binder_for_same_client(test_db, test_user):
    client = _client(test_db, "BI-SVC-003")
    _business(test_db, client.id)
    existing = Binder(
        client_id=client.id,
        binder_number=f"{client.id}/1",
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
        period_start=date.today(),
        received_at=date.today(),
        received_by=test_user.id,
        notes="existing binder path",
    )

    assert binder.id == existing.id
    assert intake.binder_id == existing.id
    assert is_new is False


def test_receive_raises_when_all_businesses_locked(test_db, test_user):
    client = _client(test_db, "BI-SVC-LOCKED-001")
    # conftest auto-creates one ACTIVE business per client; mark all as FROZEN
    test_db.query(Business).filter(Business.client_id == client.id).update(
        {"status": BusinessStatus.FROZEN}
    )
    test_db.commit()

    service = BinderIntakeService(test_db)
    with pytest.raises(AppError) as exc_info:
        service.receive(
            client_id=client.id,
            period_start=date.today(),
            received_at=date.today(),
            received_by=test_user.id,
        )

    assert exc_info.value.code == "BINDER.CLIENT_LOCKED"


def test_receive_second_binder_increments_seq(test_db, test_user):
    client = _client(test_db, "BI-SVC-SEQ-001")
    _business(test_db, client.id)

    # Seed first binder manually as already full (so service creates a new one)
    existing = Binder(
        client_id=client.id,
        binder_number=f"{client.id}/1",
        period_start=date.today(),
        created_by=test_user.id,
        status=BinderStatus.IN_OFFICE,
        is_full=True,
    )
    test_db.add(existing)
    test_db.commit()

    service = BinderIntakeService(test_db)
    binder, _, is_new = service.receive(
        client_id=client.id,
        period_start=date.today(),
        received_at=date.today(),
        received_by=test_user.id,
    )

    assert is_new is True
    assert binder.binder_number == f"{client.id}/2"
