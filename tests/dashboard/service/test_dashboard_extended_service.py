from datetime import date
from types import SimpleNamespace

from app.binders.models.binder import BinderStatus
from app.binders.services.work_state_service import WorkState
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService
from app.users.models.user import UserRole


def test_get_work_queue_uses_builder_with_pagination(test_db, monkeypatch):
    service = DashboardExtendedService(test_db)
    binder = SimpleNamespace(
        id=1,
        client_id=10,
        binder_number="DQ-1",
        received_at=date(2026, 3, 1),
        status=BinderStatus.IN_OFFICE,
    )
    client = SimpleNamespace(id=10, full_name="Queue Client")
    monkeypatch.setattr(service, "_active_binders_with_clients", lambda: [(binder, client)])
    monkeypatch.setattr(
        "app.dashboard.services.dashboard_extended_service.WorkStateService.derive_work_state",
        lambda binder, reference_date, db: WorkState.IN_PROGRESS,
    )
    monkeypatch.setattr(
        service.signals_service,
        "compute_binder_signals",
        lambda binder, reference_date: [{"key": "kpi"}],
    )

    items, total = service.get_work_queue(page=1, page_size=10, reference_date=date(2026, 3, 10))

    assert total == 1
    assert len(items) == 1
    assert items[0]["binder_id"] == 1
    assert items[0]["signals"] == [{"key": "kpi"}]


def test_get_attention_items_returns_idle_and_ready_items(test_db, monkeypatch):
    service = DashboardExtendedService(test_db)
    idle_binder = SimpleNamespace(
        id=1,
        client_id=11,
        binder_number="IDLE-1",
        received_at=date(2026, 2, 1),
        status=BinderStatus.IN_OFFICE,
    )
    ready_binder = SimpleNamespace(
        id=2,
        client_id=12,
        binder_number="READY-1",
        received_at=date(2026, 2, 15),
        status=BinderStatus.READY_FOR_PICKUP,
    )
    client_idle = SimpleNamespace(id=11, full_name="Idle Client")
    client_ready = SimpleNamespace(id=12, full_name="Ready Client")

    monkeypatch.setattr(
        service,
        "_active_binders_with_clients",
        lambda: [(idle_binder, client_idle), (ready_binder, client_ready)],
    )
    monkeypatch.setattr(
        "app.dashboard.services.dashboard_extended_service.WorkStateService.is_idle",
        lambda binder, reference_date, db: binder.id == 1,
    )

    items = service.get_attention_items(user_role=None, reference_date=date(2026, 3, 10))
    item_types = [item["item_type"] for item in items]
    assert item_types == ["idle_binder", "ready_for_pickup"]


def test_get_attention_items_advisor_skips_unmapped_charge_clients(test_db, monkeypatch):
    service = DashboardExtendedService(test_db)
    binder = SimpleNamespace(
        id=3,
        client_id=13,
        binder_number="NOATTN",
        received_at=date(2026, 2, 15),
        status=BinderStatus.IN_OFFICE,
    )
    client_obj = SimpleNamespace(id=13, full_name="No Attention")
    monkeypatch.setattr(service, "_active_binders_with_clients", lambda: [(binder, client_obj)])
    monkeypatch.setattr(
        "app.dashboard.services.dashboard_extended_service.WorkStateService.is_idle",
        lambda *_args, **_kwargs: False,
    )
    service.charge_repo = SimpleNamespace(
        list_charges=lambda **kwargs: [SimpleNamespace(client_id=999, id=1, amount=10)]
    )
    service.client_repo = SimpleNamespace(list_by_ids=lambda ids: [])

    items = service.get_attention_items(user_role=UserRole.ADVISOR, reference_date=date(2026, 3, 10))
    assert items == []
