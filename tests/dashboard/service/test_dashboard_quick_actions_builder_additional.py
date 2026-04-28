from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from app.dashboard.services import _quick_actions_helpers as helpers
from app.dashboard.services.dashboard_quick_actions_builder import build_quick_actions


def test_period_label_invalid_input_returns_original():
    assert helpers.period_label("invalid-period") == "invalid-period"


def test_build_binder_actions_returns_only_overdue_candidates():
    today = date.today()
    binders = [
        SimpleNamespace(id=1, client_record_id=10, binder_number="B1", period_start=today - timedelta(days=120), status="in_office"),
        SimpleNamespace(id=2, client_record_id=11, binder_number="B2", period_start=today - timedelta(days=10), status="in_office"),
        SimpleNamespace(id=3, client_record_id=12, binder_number="B3", period_start=today - timedelta(days=130), status="ready_for_pickup"),
        SimpleNamespace(id=4, client_record_id=13, binder_number="B4", period_start=today - timedelta(days=20), status="ready_for_pickup"),
    ]
    binder_repo = SimpleNamespace(list_active=lambda: binders)

    def fake_get_by_id(cr_id):
        return SimpleNamespace(legal_entity_id=cr_id * 100)

    business_repo = SimpleNamespace(
        db=SimpleNamespace(),
        list_by_legal_entity=lambda le_id, page=1, page_size=1: [SimpleNamespace(full_name=f"Client {le_id}")],
    )

    import unittest.mock as mock
    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository") as MockCR:
        MockCR.return_value.get_by_id = fake_get_by_id
        actions = helpers.build_binder_actions(binder_repo, business_repo)

    assert [a["binder_number"] for a in actions] == ["B1", "B3"]
    assert all(a["category"] == "binders" for a in actions)


def test_build_binder_actions_ignores_future_period_start():
    today = date.today()
    binders = [
        SimpleNamespace(
            id=5,
            client_record_id=15,
            binder_number="B5",
            period_start=today + timedelta(days=5),
            status="ready_for_pickup",
        ),
    ]
    binder_repo = SimpleNamespace(list_active=lambda: binders)
    business_repo = SimpleNamespace(
        db=SimpleNamespace(),
        list_by_legal_entity=lambda le_id, page=1, page_size=1: [SimpleNamespace(full_name="Client")],
    )

    import unittest.mock as mock
    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository") as MockCR:
        MockCR.return_value.get_by_id = lambda cr_id: SimpleNamespace(legal_entity_id=cr_id * 100)
        actions = helpers.build_binder_actions(binder_repo, business_repo)

    assert actions == []


def test_build_vat_and_annual_actions_include_due_labels():
    import unittest.mock as mock

    vat_repo = SimpleNamespace(
        list_not_filed_for_period=lambda period, limit=3: [
            SimpleNamespace(id=7, client_record_id=99),
        ]
    )
    annual_repo = SimpleNamespace(
        list_stuck_reports=lambda stale_days=7, limit=3: [
            SimpleNamespace(
                id=8,
                client_record_id=99,
                status="pending_client",
                updated_at=datetime.now(timezone.utc) - timedelta(days=9),
            )
        ]
    )
    business_repo = SimpleNamespace(
        db=SimpleNamespace(),
        list_by_legal_entity=lambda le_id, page=1, page_size=1: [
            SimpleNamespace(full_name=f"Business {le_id}")
        ],
    )

    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository") as MockCR:
        MockCR.return_value.get_by_id = lambda cr_id: SimpleNamespace(legal_entity_id=cr_id * 100)
        with mock.patch("app.dashboard.services._quick_actions_helpers.get_full_record") as full_record:
            full_record.return_value = {"full_name": "Official Client"}
            vat_actions = helpers.build_vat_actions(vat_repo, business_repo, "2026-01")
        annual_actions = helpers.build_annual_report_actions(annual_repo, business_repo)

    assert vat_actions[0]["client_name"] == "Official Client"
    assert vat_actions[0]["due_label"].startswith("תקופה:")
    assert annual_actions[0]["category"] == "annual_reports"
    assert "ימים" in annual_actions[0]["due_label"]


def test_build_quick_actions_excludes_charge_mutations(monkeypatch):
    binder_repo = object()
    vat_repo = object()
    annual_repo = object()
    business_repo = SimpleNamespace()

    monkeypatch.setattr(
        "app.dashboard.services.dashboard_quick_actions_builder.build_binder_actions",
        lambda *_: [{"key": "ready", "category": "binders"}],
    )
    monkeypatch.setattr(
        "app.dashboard.services.dashboard_quick_actions_builder.build_vat_actions",
        lambda *_: [{"key": "vat", "category": "vat"}],
    )
    monkeypatch.setattr(
        "app.dashboard.services.dashboard_quick_actions_builder.build_annual_report_actions",
        lambda *_: [{"key": "annual", "category": "annual_reports"}],
    )
    actions = build_quick_actions(
        binder_repo=binder_repo,
        business_repo=business_repo,
        vat_repo=vat_repo,
        annual_report_repo=annual_repo,
        current_period="2026-01",
    )

    assert [a["key"] for a in actions] == ["ready", "vat", "annual"]
    assert all(a.get("category") != "charges" for a in actions)
