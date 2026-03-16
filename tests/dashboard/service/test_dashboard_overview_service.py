from datetime import date

from app.users.models.user import UserRole
from app.dashboard.services.dashboard_overview_service import DashboardOverviewService


def test_get_overview_composes_quick_actions_and_attention(test_db, monkeypatch):
    service = DashboardOverviewService(test_db)
    monkeypatch.setattr(service.client_repo, "count", lambda **kwargs: 5)
    monkeypatch.setattr(service.binder_repo, "count_active", lambda **kwargs: 2)
    monkeypatch.setattr(
        service,
        "_build_quick_actions",
        lambda user_role: [{"key": "ready"}],
    )
    monkeypatch.setattr(
        service.extended_service,
        "get_attention_items",
        lambda user_role=None: [{"item_type": "idle_binder"}],
    )

    overview = service.get_overview(
        reference_date=date(2026, 3, 10),
        user_role=UserRole.ADVISOR,
    )

    assert overview["total_clients"] == 5
    assert overview["active_binders"] == 2
    assert overview["work_state"] is None
    assert overview["signals"] == []
    assert overview["quick_actions"] == [{"key": "ready"}]
    assert overview["attention"] == {
        "items": [{"item_type": "idle_binder"}],
        "total": 1,
    }
