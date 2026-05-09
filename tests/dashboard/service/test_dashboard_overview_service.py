from datetime import date

from app.users.models.user import UserRole
from app.dashboard.services.dashboard_overview_service import DashboardOverviewService


def test_get_overview_composes_quick_actions_and_attention(test_db, monkeypatch):
    service = DashboardOverviewService(test_db)
    monkeypatch.setattr(service.client_record_repo, "count", lambda **kwargs: 6)
    monkeypatch.setattr(service.binder_repo, "count_by_status", lambda _status: 2)
    monkeypatch.setattr(service.reminder_repo, "count_due_now", lambda _d: 3)
    monkeypatch.setattr(
        service.vat_stats_service,
        "build",
        lambda _d: {
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
        },
    )
    monkeypatch.setattr(
        service,
        "_build_quick_actions",
        lambda today: [{"key": "ready", "period": today.strftime("%Y-%m")}],
    )
    monkeypatch.setattr(
        service.advisor_today_service,
        "build",
        lambda today: {
            "deadline_items": [{"id": 1, "label": "מע״מ"}],
            "reminder_items": [],
        },
    )
    monkeypatch.setattr(
        service.extended_service,
        "get_attention_data",
        lambda user_role=None, reference_date=None: {
            "items": [{"item_type": "unpaid_charge"}],
            "open_charges_count": 1,
            "open_charges_amount_ils": "₪300",
        },
    )

    overview = service.get_overview(
        reference_date=date(2026, 3, 10),
        user_role=UserRole.ADVISOR,
    )

    assert overview["is_empty"] is False
    assert overview["manual_reminders_due_now"] == 3
    assert overview["open_charges_count"] == 1
    assert overview["open_charges_amount_ils"] == "₪300"
    assert overview["vat_stats"]["monthly"]["period_label"] == "פברואר 2026"
    assert overview["vat_stats"]["bimonthly"]["period_label"] == "ינואר-פברואר 2026"
    assert overview["quick_actions"] == [{"key": "ready", "period": "2026-03"}]
    assert overview["attention"] == {
        "items": [{"item_type": "unpaid_charge"}],
        "total": 1,
    }
    assert overview["advisor_today"]["deadline_items"] == [{"id": 1, "label": "מע״מ"}]
    assert overview["attention_empty_checks"] == []


def test_get_overview_empty_checks_when_no_open_charges(test_db, monkeypatch):
    service = DashboardOverviewService(test_db)
    monkeypatch.setattr(service.client_record_repo, "count", lambda **kwargs: 6)
    monkeypatch.setattr(service.binder_repo, "count_by_status", lambda _status: 0)
    monkeypatch.setattr(service.reminder_repo, "count_due_now", lambda _d: 0)
    monkeypatch.setattr(
        service.vat_stats_service,
        "build",
        lambda _d: {
            "monthly": {"period": "2026-03", "period_label": "מרץ 2026"},
            "bimonthly": {"period": "2026-02", "period_label": "ינואר-פברואר 2026"},
        },
    )
    monkeypatch.setattr(service, "_build_quick_actions", lambda today: [])
    monkeypatch.setattr(service.advisor_today_service, "build", lambda today: {})
    monkeypatch.setattr(
        service.extended_service,
        "get_attention_data",
        lambda user_role=None, reference_date=None: {
            "items": [],
            "open_charges_count": 0,
            "open_charges_amount_ils": None,
        },
    )

    overview = service.get_overview(
        reference_date=date(2026, 4, 30),
        user_role=UserRole.ADVISOR,
    )

    assert overview["is_empty"] is False
    assert overview["manual_reminders_due_now"] == 0
    assert overview["open_charges_count"] == 0
    assert overview["attention_empty_checks"] == [
        {"key": "open_charges", "label": "אין חיובים פתוחים"},
    ]


def test_get_overview_marks_empty_system(test_db, monkeypatch):
    service = DashboardOverviewService(test_db)
    monkeypatch.setattr(service.client_record_repo, "count", lambda **kwargs: 0)
    monkeypatch.setattr(service.binder_repo, "count_by_status", lambda _status: 0)
    monkeypatch.setattr(service.reminder_repo, "count_due_now", lambda _d: 0)
    monkeypatch.setattr(
        service.vat_stats_service,
        "build",
        lambda _d: {
            "monthly": {"period": "2026-03", "period_label": "מרץ 2026"},
            "bimonthly": {"period": "2026-02", "period_label": "ינואר-פברואר 2026"},
        },
    )
    monkeypatch.setattr(service, "_build_quick_actions", lambda today: [])
    monkeypatch.setattr(service.advisor_today_service, "build", lambda today: {})
    monkeypatch.setattr(
        service.extended_service,
        "get_attention_data",
        lambda user_role=None, reference_date=None: {
            "items": [],
            "open_charges_count": 0,
            "open_charges_amount_ils": None,
        },
    )

    overview = service.get_overview(reference_date=date(2026, 4, 30))

    assert overview["is_empty"] is True
