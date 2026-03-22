from datetime import date

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.binder_service import BinderService
from app.clients.models.client import Client


def _create_client(db) -> Client:
    client = Client(
        full_name="Binder Client",
        id_number="B-100",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _create_binder(db, client_id: int, user_id: int, number: str, status: BinderStatus):
    repo = BinderRepository(db)
    binder = repo.create(
        client_id=client_id,
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
    active = service.list_active_binders(client_id=client.id)

    assert len(active) == 1
    assert active[0].status == BinderStatus.IN_OFFICE
