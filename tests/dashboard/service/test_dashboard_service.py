from datetime import date

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.models.client import Client
from app.dashboard.services.dashboard_service import DashboardService


def _client(db) -> Client:
    client = Client(
        full_name="Dash Client",
        id_number="D-001",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _binder(db, client_id: int, user_id: int, number: str, status: BinderStatus):
    repo = BinderRepository(db)
    binder = repo.create(
        client_id=client_id,
        binder_number=number,
        period_start=date(2024, 1, 5),
        created_by=user_id,
    )
    if status != BinderStatus.IN_OFFICE:
        repo.update_status(binder.id, status, binder=binder)
    return binder


def test_get_summary_counts_statuses_and_attention(monkeypatch, test_db, test_user):
    client = _client(test_db)
    _binder(test_db, client.id, test_user.id, "D-001", BinderStatus.IN_OFFICE)
    _binder(test_db, client.id, test_user.id, "D-002", BinderStatus.READY_FOR_PICKUP)

    service = DashboardService(test_db)
    monkeypatch.setattr(service.extended_service, "get_attention_items", lambda user_role=None: [{"id": 1}])

    summary = service.get_summary()

    assert summary["binders_in_office"] == 1
    assert summary["binders_ready_for_pickup"] == 1
    assert summary["attention"]["items"] == [{"id": 1}]
    assert summary["attention"]["total"] == 1
