from datetime import date, timedelta

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.binder_operations_service import BinderOperationsService
from app.binders.services.work_state_service import WorkState
from app.clients.models.client import Client


def _create_client(db, name: str, id_number: str) -> Client:
    client = Client(
        full_name=name,
        id_number=id_number,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _create_binder(db, client_id: int, user_id: int, number: str, period_start: date, status: BinderStatus):
    repo = BinderRepository(db)
    binder = repo.create(
        client_id=client_id,
        binder_number=number,
        period_start=period_start,
        created_by=user_id,
    )
    if status != BinderStatus.IN_OFFICE:
        binder.status = status
        db.commit()
        db.refresh(binder)
    return binder


def test_get_open_binders_filters_returned_and_orders(test_db, test_user):
    client = _create_client(test_db, "Client A", "C-001")
    newer = _create_binder(
        test_db, client.id, test_user.id, "B-NEW", date(2024, 2, 1), BinderStatus.IN_OFFICE
    )
    older = _create_binder(
        test_db, client.id, test_user.id, "B-OLD", date(2024, 1, 1), BinderStatus.IN_OFFICE
    )
    _create_binder(
        test_db, client.id, test_user.id, "B-RET", date(2024, 1, 15), BinderStatus.RETURNED
    )

    service = BinderOperationsService(test_db)
    items, total = service.get_open_binders(page=1, page_size=10)

    assert total == 2
    assert [b.id for b in items] == [newer.id, older.id]


def test_get_client_binders_scopes_to_client(test_db, test_user):
    client_a = _create_client(test_db, "Client A", "C-010")
    client_b = _create_client(test_db, "Client B", "C-011")
    target = _create_binder(
        test_db, client_a.id, test_user.id, "B-CLI-A", date(2024, 1, 5), BinderStatus.IN_OFFICE
    )
    _create_binder(
        test_db, client_b.id, test_user.id, "B-CLI-B", date(2024, 1, 6), BinderStatus.IN_OFFICE
    )

    service = BinderOperationsService(test_db)
    items, total = service.get_client_binders(client_id=client_a.id, page=1, page_size=10)

    assert total == 1
    assert items[0].id == target.id


def test_client_exists_returns_boolean(test_db):
    client = _create_client(test_db, "Client C", "C-020")
    service = BinderOperationsService(test_db)

    assert service.client_exists(client.id) is True
    assert service.client_exists(9999) is False


def test_enrich_binder_includes_work_state_and_signals(test_db, test_user):
    client = _create_client(test_db, "Client D", "C-030")
    idle_binder = _create_binder(
        test_db,
        client.id,
        test_user.id,
        "B-IDLE",
        date.today() - timedelta(days=30),
        BinderStatus.IN_OFFICE,
    )

    service = BinderOperationsService(test_db)
    enriched = service.enrich_binder(idle_binder, db=test_db)

    assert enriched["id"] == idle_binder.id
    assert enriched["work_state"] == WorkState.WAITING_FOR_WORK.value
    assert "idle_binder" in enriched["signals"]
