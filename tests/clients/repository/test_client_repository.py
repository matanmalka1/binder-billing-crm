from app.clients.models.client import Client, IdNumberType
from app.clients.repositories.client_repository import ClientRepository


def _create_client(db, *, full_name: str, id_number: str, deleted: bool = False) -> Client:
    repo = ClientRepository(db)
    client = repo.create(
        full_name=full_name,
        id_number=id_number,
        id_number_type=IdNumberType.CORPORATION,
        created_by=1,
    )
    if deleted:
        repo.soft_delete(client.id, deleted_by=2)
        client = repo.get_by_id_including_deleted(client.id)
    return client


def test_create_and_get_by_id_filters_deleted(test_db):
    repo = ClientRepository(test_db)
    created = repo.create(
        full_name="Repo Client",
        id_number="100000001",
        id_number_type=IdNumberType.CORPORATION,
        created_by=1,
    )

    assert repo.get_by_id(created.id) is not None

    assert repo.soft_delete(created.id, deleted_by=99) is True
    assert repo.get_by_id(created.id) is None
    assert repo.get_by_id_including_deleted(created.id) is not None


def test_get_active_and_deleted_by_id_number(test_db):
    repo = ClientRepository(test_db)
    active = _create_client(test_db, full_name="Active", id_number="200000001")
    deleted = _create_client(test_db, full_name="Deleted", id_number="200000002", deleted=True)

    active_rows = repo.get_active_by_id_number("200000001")
    deleted_rows = repo.get_deleted_by_id_number("200000002")
    all_rows_active = repo.get_all_by_id_number("200000001")
    all_rows_deleted = repo.get_all_by_id_number("200000002")

    assert [c.id for c in active_rows] == [active.id]
    assert [c.id for c in deleted_rows] == [deleted.id]
    assert [c.id for c in all_rows_active] == [active.id]
    assert [c.id for c in all_rows_deleted] == [deleted.id]


def test_restore_clears_deleted_fields(test_db):
    client = _create_client(test_db, full_name="Restore Me", id_number="300000001", deleted=True)
    repo = ClientRepository(test_db)

    restored = repo.restore(client.id, restored_by=7)

    assert restored is not None
    assert restored.deleted_at is None
    assert restored.deleted_by is None
    assert restored.restored_at is not None
    assert restored.restored_by == 7


def test_list_count_search_and_list_by_ids(test_db):
    _create_client(test_db, full_name="Alice One", id_number="400000001")
    bob = _create_client(test_db, full_name="Bob Two", id_number="400000002")
    deleted = _create_client(test_db, full_name="Deleted Three", id_number="499999999", deleted=True)

    repo = ClientRepository(test_db)

    items_page_1 = repo.list(page=1, page_size=1)
    assert len(items_page_1) == 1

    search_items, search_total = repo.search(query="Bob", page=1, page_size=10)
    assert search_total == 1
    assert [c.id for c in search_items] == [bob.id]

    filtered = repo.count(search="40000000")
    assert filtered == 2

    by_ids = repo.list_by_ids([bob.id, deleted.id])
    assert [c.id for c in by_ids] == [bob.id]


def test_update_ignores_unknown_fields(test_db):
    client = _create_client(test_db, full_name="Old Name", id_number="500000001")
    repo = ClientRepository(test_db)

    updated = repo.update(client.id, full_name="New Name", does_not_exist="x")

    assert updated is not None
    assert updated.full_name == "New Name"
    assert not hasattr(updated, "does_not_exist")
