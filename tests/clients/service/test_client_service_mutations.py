import pytest
from sqlalchemy.exc import IntegrityError

from app.clients.models.client import IdNumberType
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_service import ClientService
from app.core.exceptions import ConflictError, NotFoundError


def _create_client(db, *, full_name: str, id_number: str):
    return ClientRepository(db).create(
        full_name=full_name,
        id_number=id_number,
        id_number_type=IdNumberType.CORPORATION,
        created_by=1,
    )


def test_create_client_success(test_db):
    service = ClientService(test_db)

    created = service.create_client(
        full_name="Service Client",
        id_number="610000001",
        id_number_type=IdNumberType.CORPORATION,
        actor_id=3,
    )

    assert created.id is not None
    assert created.created_by == 3


def test_create_client_conflict_when_active_exists(test_db):
    _create_client(test_db, full_name="Existing", id_number="620000001")
    service = ClientService(test_db)

    with pytest.raises(ConflictError) as exc:
        service.create_client(
            full_name="Duplicate",
            id_number="620000001",
            id_number_type=IdNumberType.CORPORATION,
        )

    assert exc.value.code == "CLIENT.CONFLICT"


def test_create_client_deleted_exists_conflict(test_db):
    repo = ClientRepository(test_db)
    existing = repo.create(
        full_name="Deleted",
        id_number="630000001",
        id_number_type=IdNumberType.CORPORATION,
        created_by=1,
    )
    repo.soft_delete(existing.id, deleted_by=1)

    service = ClientService(test_db)
    with pytest.raises(ConflictError) as exc:
        service.create_client(
            full_name="New",
            id_number="630000001",
            id_number_type=IdNumberType.CORPORATION,
        )

    assert exc.value.code == "CLIENT.DELETED_EXISTS"


def test_get_client_or_raise_not_found(test_db):
    service = ClientService(test_db)

    with pytest.raises(NotFoundError) as exc:
        service.get_client_or_raise(999)

    assert exc.value.code == "CLIENT.NOT_FOUND"


def test_update_delete_restore_flow(test_db):
    service = ClientService(test_db)
    created = service.create_client(
        full_name="Before Update",
        id_number="640000001",
        id_number_type=IdNumberType.CORPORATION,
    )

    updated = service.update_client(created.id, full_name="After Update", phone="0501234567")
    assert updated.full_name == "After Update"
    assert updated.phone == "0501234567"

    service.delete_client(created.id, actor_id=11)
    assert service.get_client(created.id) is None

    restored = service.restore_client(created.id, actor_id=12)
    assert restored.deleted_at is None
    assert restored.restored_by == 12


def test_delete_raises_not_found_when_client_already_deleted(test_db):
    service = ClientService(test_db)
    created = service.create_client(
        full_name="Delete Twice",
        id_number="640000009",
        id_number_type=IdNumberType.CORPORATION,
    )
    service.delete_client(created.id, actor_id=1)

    with pytest.raises(NotFoundError) as exc:
        service.delete_client(created.id, actor_id=2)

    assert exc.value.code == "CLIENT.NOT_FOUND"


def test_restore_raises_when_not_deleted(test_db):
    client = _create_client(test_db, full_name="Alive", id_number="650000001")
    service = ClientService(test_db)

    with pytest.raises(ConflictError) as exc:
        service.restore_client(client.id, actor_id=1)

    assert exc.value.code == "CLIENT.NOT_DELETED"


def test_restore_raises_when_active_duplicate_exists(test_db):
    repo = ClientRepository(test_db)
    deleted = repo.create(
        full_name="Old",
        id_number="660000001",
        id_number_type=IdNumberType.CORPORATION,
        created_by=1,
    )
    repo.soft_delete(deleted.id, deleted_by=1)

    repo.create(
        full_name="Current Active",
        id_number="660000001",
        id_number_type=IdNumberType.CORPORATION,
        created_by=1,
    )

    service = ClientService(test_db)
    with pytest.raises(ConflictError) as exc:
        service.restore_client(deleted.id, actor_id=2)

    assert exc.value.code == "CLIENT.CONFLICT"


def test_list_clients_and_conflict_info(test_db):
    service = ClientService(test_db)
    one = service.create_client(
        full_name="Alpha",
        id_number="670000001",
        id_number_type=IdNumberType.CORPORATION,
    )
    two = service.create_client(
        full_name="Beta",
        id_number="670000002",
        id_number_type=IdNumberType.CORPORATION,
    )
    service.delete_client(two.id, actor_id=1)

    items, total = service.list_clients(search="Alpha", page=1, page_size=10)
    assert total == 1
    assert [c.id for c in items] == [one.id]

    info_active = service.get_conflict_info("670000001")
    assert len(info_active["active_clients"]) == 1
    assert len(info_active["deleted_clients"]) == 0

    info_deleted = service.get_conflict_info("670000002")
    assert len(info_deleted["active_clients"]) == 0
    assert len(info_deleted["deleted_clients"]) == 1


def test_create_client_converts_integrity_error_to_conflict(test_db, monkeypatch):
    service = ClientService(test_db)

    def _raise_integrity(**_kwargs):
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr(service.client_repo, "create", _raise_integrity)

    with pytest.raises(ConflictError) as exc:
        service.create_client(
            full_name="Integrity",
            id_number="690000001",
            id_number_type=IdNumberType.CORPORATION,
        )

    assert exc.value.code == "CLIENT.CONFLICT"


def test_restore_raises_not_found_when_client_missing(test_db):
    service = ClientService(test_db)

    with pytest.raises(NotFoundError) as exc:
        service.restore_client(9999, actor_id=1)

    assert exc.value.code == "CLIENT.NOT_FOUND"


def test_restore_raises_not_found_when_repo_restore_returns_none(test_db, monkeypatch):
    service = ClientService(test_db)
    created = service.create_client(
        full_name="To Restore",
        id_number="690000002",
        id_number_type=IdNumberType.CORPORATION,
    )
    service.delete_client(created.id, actor_id=1)

    monkeypatch.setattr(service.client_repo, "restore", lambda *_args, **_kwargs: None)

    with pytest.raises(NotFoundError) as exc:
        service.restore_client(created.id, actor_id=2)

    assert exc.value.code == "CLIENT.NOT_FOUND"
