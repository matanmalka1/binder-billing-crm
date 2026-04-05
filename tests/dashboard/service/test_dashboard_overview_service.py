from datetime import date

from app.users.models.user import UserRole
from app.dashboard.services.dashboard_overview_service import DashboardOverviewService


def test_get_overview_composes_quick_actions_and_attention(test_db, monkeypatch):
    service = DashboardOverviewService(test_db)
    monkeypatch.setattr(service.business_repo, "count", lambda **kwargs: 5)
    monkeypatch.setattr(service.binder_repo, "count_active", lambda **kwargs: 2)
    monkeypatch.setattr(service.reminder_repo, "count_pending_by_date", lambda _d: 3)
    monkeypatch.setattr(service.vat_repo, "count_by_period_not_filed", lambda _p: 4)
    monkeypatch.setattr(
        service,
        "_build_quick_actions",
        lambda user_role, current_period: [{"key": "ready", "period": current_period}],
    )
    monkeypatch.setattr(
        service.extended_service,
        "get_attention_items",
        lambda user_role=None: [{"item_type": "ready_for_pickup"}],
    )

    overview = service.get_overview(
        reference_date=date(2026, 3, 10),
        user_role=UserRole.ADVISOR,
    )

    assert overview["total_clients"] == 5
    assert overview["active_binders"] == 2
    assert overview["open_reminders"] == 3
    assert overview["vat_due_this_month"] == 4
    assert overview["quick_actions"] == [{"key": "ready", "period": "2026-03"}]
    assert overview["attention"] == {
        "items": [{"item_type": "ready_for_pickup"}],
        "total": 1,
    }
