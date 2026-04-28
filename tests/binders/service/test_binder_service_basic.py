from datetime import date

from app.binders.models.binder import BinderStatus
from app.binders.models.binder_intake import BinderIntake
from app.binders.models.binder_intake_material import BinderIntakeMaterial, MaterialType
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.binder_service import BinderService
from tests.helpers.identity import SeededClient, seed_client_identity


def _create_client(db) -> SeededClient:
    return seed_client_identity(
        db,
        full_name="Binder Client",
        id_number="B-100",
    )


def _create_binder(db, client_id: int, user_id: int, number: str, status: BinderStatus):
    repo = BinderRepository(db)
    binder = repo.create(
        client_record_id=client_id,
        binder_number=number,
        period_start=date(2024, 1, 10),
        created_by=user_id,
    )
    if status != BinderStatus.IN_OFFICE:
        binder.status = status
        db.commit()
        db.refresh(binder)
    return binder


def test_get_binder_returns_entity(test_db, test_user):
    client = _create_client(test_db)
    binder = _create_binder(test_db, client.id, test_user.id, "BIN-001", BinderStatus.IN_OFFICE)

    service = BinderService(test_db)
    fetched = service.get_binder(binder.id)

    assert fetched is not None
    assert fetched.id == binder.id


def test_delete_binder_soft_deletes_and_returns_true(test_db, test_user):
    client = _create_client(test_db)
    binder = _create_binder(test_db, client.id, test_user.id, "BIN-002", BinderStatus.IN_OFFICE)
    service = BinderService(test_db)

    deleted = service.delete_binder(binder.id, actor_id=test_user.id)

    assert deleted is True
    assert service.get_binder(binder.id) is None


def test_delete_binder_missing_returns_false(test_db):
    service = BinderService(test_db)

    assert service.delete_binder(999, actor_id=1) is False


def test_list_active_binders_excludes_returned(test_db, test_user):
    client = _create_client(test_db)
    _create_binder(test_db, client.id, test_user.id, "BIN-003", BinderStatus.IN_OFFICE)
    _create_binder(test_db, client.id, test_user.id, "BIN-004", BinderStatus.RETURNED)

    service = BinderService(test_db)
    active = service.list_active_binders(client_record_id=client.id)

    assert len(active) == 1
    assert active[0].status == BinderStatus.IN_OFFICE


def test_mark_ready_bulk_marks_only_eligible_binders(test_db, test_user):
    client = _create_client(test_db)
    eligible = _create_binder(test_db, client.id, test_user.id, "BIN-005", BinderStatus.IN_OFFICE)
    too_new = _create_binder(test_db, client.id, test_user.id, "BIN-006", BinderStatus.CLOSED_IN_OFFICE)
    returned = _create_binder(test_db, client.id, test_user.id, "BIN-007", BinderStatus.RETURNED)

    for binder, month in ((eligible, 1), (too_new, 3)):
        intake = BinderIntake(
            binder_id=binder.id,
            received_at=date(2026, month, 20),
            received_by=test_user.id,
        )
        test_db.add(intake)
        test_db.flush()
        test_db.add(
            BinderIntakeMaterial(
                intake_id=intake.id,
                material_type=MaterialType.OTHER,
                period_year=2026,
                period_month_start=month,
                period_month_end=month,
            )
        )

    test_db.commit()

    service = BinderService(test_db)
    updated = service.mark_ready_bulk(
        client_record_id=client.id,
        until_period_year=2026,
        until_period_month=2,
        user_id=test_user.id,
    )

    assert [binder.id for binder in updated] == [eligible.id]
    assert service.get_binder(eligible.id).status == BinderStatus.READY_FOR_PICKUP
    assert service.get_binder(eligible.id).ready_for_pickup_at is not None
    assert service.get_binder(too_new.id).status == BinderStatus.CLOSED_IN_OFFICE
    assert service.get_binder(returned.id).status == BinderStatus.RETURNED
