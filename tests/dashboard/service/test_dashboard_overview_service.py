from datetime import date

from app.users.models.user import UserRole
from app.dashboard.services.dashboard_overview_service import DashboardOverviewService

_VAT_STUB = {
    "monthly": {
        "period": "2026-02",
        "period_label": "פברואר 2026",
        "submitted": 2,
        "required": 3,
        "pending": 1,
        "completion_percent": 67,
    },
    "bimonthly": {
        "period": "2026-02",
        "period_label": "ינואר-פברואר 2026",
        "submitted": 4,
        "required": 4,
        "pending": 0,
        "completion_percent": 100,
    },
}


def test_get_overview_composes_quick_actions_and_attention(test_db, monkeypatch):
    service = DashboardOverviewService(test_db)
    monkeypatch.setattr(service.client_record_repo, "count", lambda **kwargs: 6)
    monkeypatch.setattr(service.vat_stats_service, "build", lambda _d: _VAT_STUB)
    monkeypatch.setattr(
        service,
        "_build_quick_actions",
        lambda today: [{"key": "ready", "period": today.strftime("%Y-%m")}],
    )
    monkeypatch.setattr(
        service.advisor_today_service,
        "build",
        lambda today: {"deadline_items": [{"id": 1, "label": "מע״מ"}]},
    )
    monkeypatch.setattr(
        service.attention_service,
        "build",
        lambda user_role=None, reference_date=None: [{"source_type": "charge"}],
    )
    monkeypatch.setattr(service.charge_repo, "count_charges", lambda **kwargs: 1)
    monkeypatch.setattr(service.charge_repo, "sum_open_charges_amount", lambda: None)

    overview = service.get_overview(
        reference_date=date(2026, 3, 10),
        user_role=UserRole.ADVISOR,
    )

    assert overview["is_empty"] is False
    assert overview["open_charges_count"] == 1
    assert overview["vat_stats"]["monthly"]["period_label"] == "פברואר 2026"
    assert overview["quick_actions"] == [{"key": "ready", "period": "2026-03"}]
    assert overview["attention"] == {
        "items": [{"source_type": "charge"}],
        "total": 1,
    }
    assert overview["advisor_today"]["deadline_items"] == [{"id": 1, "label": "מע״מ"}]


def test_get_overview_marks_empty_system(test_db, monkeypatch):
    service = DashboardOverviewService(test_db)
    monkeypatch.setattr(service.client_record_repo, "count", lambda **kwargs: 0)
    monkeypatch.setattr(service.vat_stats_service, "build", lambda _d: _VAT_STUB)
    monkeypatch.setattr(service, "_build_quick_actions", lambda today: [])
    monkeypatch.setattr(service.advisor_today_service, "build", lambda today: {})
    monkeypatch.setattr(
        service.attention_service,
        "build",
        lambda user_role=None, reference_date=None: [],
    )
    monkeypatch.setattr(service.charge_repo, "count_charges", lambda **kwargs: 0)

    overview = service.get_overview(reference_date=date(2026, 4, 30))

    assert overview["is_empty"] is True


def test_get_overview_secretary_gets_no_attention_or_quick_actions(
    test_db, monkeypatch
):
    service = DashboardOverviewService(test_db)
    monkeypatch.setattr(service.client_record_repo, "count", lambda **kwargs: 3)
    monkeypatch.setattr(service.vat_stats_service, "build", lambda _d: _VAT_STUB)

    overview = service.get_overview(
        reference_date=date(2026, 4, 30),
        user_role=UserRole.SECRETARY,
    )

    assert overview["quick_actions"] == []
    assert overview["attention"]["items"] == []
    assert overview["open_charges_count"] == 0
