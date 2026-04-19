from datetime import date

import pytest

from app.binders.models.binder import Binder, BinderStatus
from app.binders.services.binder_intake_service import BinderIntakeService
from app.businesses.models.business import Business, BusinessStatus
from app.clients.models.client import Client
from app.core.exceptions import AppError


def _client(db, id_number: str, office_client_number: int) -> Client:
    client = Client(
        full_name=f"Binder Intake {id_number}",
        id_number=id_number,
        office_client_number=office_client_number,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _business(db, client_id: int, status: BusinessStatus = BusinessStatus.ACTIVE) -> Business:
    biz = Business(
        client_id=client_id,
        business_name=f"Business {client_id}",
        status=status,
        opened_at=date.today(),
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)
    return biz


def _materials(year: int = 2026, month: int = 2) -> list[dict]:
    return [
        {
            "material_type": "other",
            "period_year": year,
            "period_month_start": month,
            "period_month_end": month,
            "description": "test material",
        }
    ]


def test_receive_creates_composite_binder_label(test_db, test_user):
    client = _client(test_db, "BI-SVC-NEW-001", office_client_number=301)
    _business(test_db, client.id)

    service = BinderIntakeService(test_db)
    binder, _, is_new = service.receive(
        client_id=client.id,
        received_at=date.today(),
        received_by=test_user.id,
        materials=_materials(),
    )

    assert is_new is True
    assert binder.binder_number == "301/1"
    assert binder.period_start == date(2026, 2, 1)


def test_receive_reuses_existing_binder_for_same_client(test_db, test_user):
    client = _client(test_db, "BI-SVC-003", office_client_number=302)
    _business(test_db, client.id)
    existing = Binder(
        client_id=client.id,
        binder_number="302/1",
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
        received_at=date.today(),
        received_by=test_user.id,
        notes="existing binder path",
        materials=_materials(),
    )

    assert binder.id == existing.id
    assert intake.binder_id == existing.id
    assert is_new is False


def test_receive_backfills_period_start_for_existing_binder_without_period(test_db, test_user):
    client = _client(test_db, "BI-SVC-BACKFILL-001", office_client_number=307)
    _business(test_db, client.id)
    existing = Binder(
        client_id=client.id,
        binder_number="307/1",
        period_start=None,
        created_by=test_user.id,
        status=BinderStatus.IN_OFFICE,
    )
    test_db.add(existing)
    test_db.commit()
    test_db.refresh(existing)

    service = BinderIntakeService(test_db)
    binder, intake, is_new = service.receive(
        client_id=client.id,
        received_at=date.today(),
        received_by=test_user.id,
        notes="backfill period start",
        materials=_materials(year=2026, month=4),
    )

    assert binder.id == existing.id
    assert intake.binder_id == existing.id
    assert is_new is False
    assert binder.period_start == date(2026, 4, 1)


def test_receive_raises_when_all_businesses_locked(test_db, test_user):
    client = _client(test_db, "BI-SVC-LOCKED-001", office_client_number=303)
    _business(test_db, client.id)
    test_db.query(Business).filter(Business.client_id == client.id).update(
        {"status": BusinessStatus.FROZEN}
    )
    test_db.commit()

    service = BinderIntakeService(test_db)
    with pytest.raises(AppError) as exc_info:
        service.receive(
            client_id=client.id,
            received_at=date.today(),
            received_by=test_user.id,
            materials=_materials(),
        )

    assert exc_info.value.code == "BINDER.CLIENT_LOCKED"


def test_receive_second_binder_increments_seq_after_closed_binder(test_db, test_user):
    client = _client(test_db, "BI-SVC-SEQ-001", office_client_number=304)
    _business(test_db, client.id)

    existing = Binder(
        client_id=client.id,
        binder_number="304/1",
        period_start=date.today(),
        created_by=test_user.id,
        status=BinderStatus.CLOSED_IN_OFFICE,
    )
    test_db.add(existing)
    test_db.commit()

    service = BinderIntakeService(test_db)
    binder, _, is_new = service.receive(
        client_id=client.id,
        received_at=date.today(),
        received_by=test_user.id,
        materials=_materials(month=3),
    )

    assert is_new is True
    assert binder.binder_number == "304/2"
    assert binder.period_start == date(2026, 3, 1)


def test_receive_old_period_prefers_matching_closed_binder(test_db, test_user):
    client = _client(test_db, "BI-SVC-OLD-001", office_client_number=305)
    _business(test_db, client.id)

    old_binder = Binder(
        client_id=client.id,
        binder_number="305/1",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 2, 28),
        created_by=test_user.id,
        status=BinderStatus.CLOSED_IN_OFFICE,
    )
    active_binder = Binder(
        client_id=client.id,
        binder_number="305/2",
        period_start=date(2026, 3, 1),
        created_by=test_user.id,
        status=BinderStatus.IN_OFFICE,
    )
    test_db.add(old_binder)
    test_db.add(active_binder)
    test_db.commit()
    test_db.refresh(old_binder)
    test_db.refresh(active_binder)

    service = BinderIntakeService(test_db)
    binder, intake, is_new = service.receive(
        client_id=client.id,
        received_at=date(2026, 4, 5),
        received_by=test_user.id,
        open_new_binder=True,
        materials=_materials(year=2026, month=2),
    )

    assert is_new is False
    assert binder.id == old_binder.id
    assert intake.binder_id == old_binder.id
    assert test_db.get(Binder, active_binder.id).status == BinderStatus.IN_OFFICE


def test_receive_old_period_falls_back_to_active_binder_with_note(test_db, test_user):
    client = _client(test_db, "BI-SVC-OLD-002", office_client_number=306)
    _business(test_db, client.id)

    closed_binder = Binder(
        client_id=client.id,
        binder_number="306/1",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        created_by=test_user.id,
        status=BinderStatus.CLOSED_IN_OFFICE,
    )
    active_binder = Binder(
        client_id=client.id,
        binder_number="306/2",
        period_start=date(2026, 3, 1),
        created_by=test_user.id,
        status=BinderStatus.IN_OFFICE,
    )
    test_db.add(closed_binder)
    test_db.add(active_binder)
    test_db.commit()
    test_db.refresh(active_binder)

    service = BinderIntakeService(test_db)
    binder, intake, is_new = service.receive(
        client_id=client.id,
        received_at=date(2026, 4, 5),
        received_by=test_user.id,
        open_new_binder=True,
        notes="old-period material arrived after the binder was already closed",
        materials=_materials(year=2026, month=2),
    )

    assert is_new is False
    assert binder.id == active_binder.id
    assert intake.binder_id == active_binder.id
    refreshed_active = test_db.get(Binder, active_binder.id)
    assert refreshed_active.status == BinderStatus.IN_OFFICE
    assert refreshed_active.period_end is None
