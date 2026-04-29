"""Tests for the refactored quick actions helpers and builder."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import unittest.mock as mock

from app.dashboard.services import _quick_actions_helpers as helpers
from app.dashboard.services.dashboard_quick_actions_builder import build_quick_actions


def _make_notification_repo(last=None):
    return SimpleNamespace(
        get_last_for_binder_trigger=lambda binder_id, trigger: last,
        get_last_for_annual_report_trigger=lambda report_id, trigger: last,
    )


def _make_business_repo(name="Client"):
    return SimpleNamespace(
        db=SimpleNamespace(),
        list_by_legal_entity=lambda le_id, page=1, page_size=1: [SimpleNamespace(full_name=name)],
    )


# ── VAT ──────────────────────────────────────────────────────────────────────

def test_build_vat_actions_overdue():
    today = date(2026, 4, 28)
    period = "2026-03"  # deadline was 2026-03-15, clearly overdue
    item = SimpleNamespace(id=1, client_record_id=10, period=period)
    from app.vat_reports.models.vat_enums import VatWorkItemStatus
    item.status = VatWorkItemStatus.PENDING_MATERIALS
    vat_repo = SimpleNamespace(list_open_up_to_period=lambda up_to, limit=50: [item])
    business_repo = _make_business_repo()

    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository") as MockCR:
        MockCR.return_value.get_by_id = lambda cr_id: SimpleNamespace(legal_entity_id=cr_id * 100)
        with mock.patch("app.dashboard.services._quick_actions_helpers.get_full_record") as mock_fr:
            mock_fr.return_value = {"full_name": "Client A"}
            actions = helpers.build_vat_actions(vat_repo, business_repo, today)

    assert len(actions) == 1
    assert actions[0]["urgency"] == "overdue"
    assert actions[0]["due_label"] == 'דוח מע״מ · מרץ 2026 · באיחור 44 ימים'
    assert actions[0]["description"] == "ממתין לחומרים"
    assert actions[0]["category"] == "vat"


def test_build_vat_actions_upcoming():
    today = date(2026, 4, 10)  # day 10, so >= 8, current period
    period = "2026-04"
    item = SimpleNamespace(
        id=2, client_record_id=11, period=period,
    )
    from app.vat_reports.models.vat_enums import VatWorkItemStatus
    item.status = VatWorkItemStatus.PENDING_MATERIALS
    vat_repo = SimpleNamespace(list_open_up_to_period=lambda up_to, limit=50: [item])
    business_repo = _make_business_repo()

    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository") as MockCR:
        MockCR.return_value.get_by_id = lambda cr_id: SimpleNamespace(legal_entity_id=cr_id * 100)
        with mock.patch("app.dashboard.services._quick_actions_helpers.get_full_record") as mock_fr:
            mock_fr.return_value = {"full_name": "Client B"}
            actions = helpers.build_vat_actions(vat_repo, business_repo, today)

    assert len(actions) == 1
    assert actions[0]["urgency"] == "upcoming"
    assert actions[0]["due_label"] == 'דוח מע״מ · אפריל 2026 · עוד 5 ימים'
    assert actions[0]["description"] == "ממתין לחומרים"


def test_build_vat_actions_too_early_not_shown():
    today = date(2026, 4, 5)  # day 5, before threshold of 8
    period = "2026-04"
    item = SimpleNamespace(id=3, client_record_id=12, period=period)
    vat_repo = SimpleNamespace(list_open_up_to_period=lambda up_to, limit=50: [item])
    business_repo = _make_business_repo()

    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository") as MockCR:
        MockCR.return_value.get_by_id = lambda cr_id: SimpleNamespace(legal_entity_id=cr_id * 100)
        with mock.patch("app.dashboard.services._quick_actions_helpers.get_full_record") as mock_fr:
            mock_fr.return_value = {"full_name": "Client C"}
            actions = helpers.build_vat_actions(vat_repo, business_repo, today)

    assert actions == []


# ── Binders ───────────────────────────────────────────────────────────────────

def test_build_binder_actions_shows_overdue_pickup():
    now = datetime.now(timezone.utc)
    binder = SimpleNamespace(
        id=1, client_record_id=10, binder_number="B1",
        ready_for_pickup_at=now - timedelta(days=35),
        status="ready_for_pickup",
    )
    binder_repo = SimpleNamespace(list_overdue_pickup=lambda overdue_days=30, limit=50: [binder])
    business_repo = _make_business_repo()
    notification_repo = _make_notification_repo(last=None)

    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository") as MockCR:
        MockCR.return_value.get_by_id = lambda cr_id: SimpleNamespace(legal_entity_id=cr_id * 100)
        actions = helpers.build_binder_actions(binder_repo, business_repo, notification_repo)

    assert len(actions) == 1
    assert actions[0]["key"] == "binder_pickup_reminder"
    assert actions[0]["category"] == "binders"
    assert actions[0]["urgency"] == "overdue"


def test_build_binder_actions_skips_recent_reminder():
    now = datetime.now(timezone.utc)
    binder = SimpleNamespace(
        id=2, client_record_id=11, binder_number="B2",
        ready_for_pickup_at=now - timedelta(days=35),
        status="ready_for_pickup",
    )
    binder_repo = SimpleNamespace(list_overdue_pickup=lambda overdue_days=30, limit=50: [binder])
    business_repo = _make_business_repo()
    recent_notification = SimpleNamespace(created_at=now - timedelta(days=2))
    notification_repo = _make_notification_repo(last=recent_notification)

    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository") as MockCR:
        MockCR.return_value.get_by_id = lambda cr_id: SimpleNamespace(legal_entity_id=cr_id * 100)
        actions = helpers.build_binder_actions(binder_repo, business_repo, notification_repo)

    assert actions == []


# ── Annual Reports ────────────────────────────────────────────────────────────

def test_build_annual_report_actions_overdue_navigate():
    today = date(2026, 4, 28)
    deadline = datetime(2026, 3, 31, tzinfo=timezone.utc)
    from app.annual_reports.models.annual_report_enums import AnnualReportStatus
    report = SimpleNamespace(
        id=1, client_record_id=10, tax_year=2025,
        status=AnnualReportStatus.IN_PREPARATION,
        filing_deadline=deadline,
        updated_at=datetime.now(timezone.utc) - timedelta(days=20),
    )
    annual_repo = SimpleNamespace(list_for_dashboard=lambda limit=50: [report])
    business_repo = _make_business_repo()
    notification_repo = _make_notification_repo()

    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository"), \
         mock.patch("app.dashboard.services._quick_actions_helpers.get_full_record", return_value={"full_name": "Test Client"}):
        actions = helpers.build_annual_report_actions(annual_repo, business_repo, notification_repo, today)

    assert len(actions) == 1
    assert actions[0]["urgency"] == "overdue"
    assert actions[0]["key"] == "annual_report_navigate"


def test_build_annual_report_actions_pending_client_reminder():
    today = date(2026, 4, 28)
    deadline = datetime(2026, 4, 30, tzinfo=timezone.utc)  # 2 days away — within upcoming window
    from app.annual_reports.models.annual_report_enums import AnnualReportStatus
    report = SimpleNamespace(
        id=2, client_record_id=11, tax_year=2025,
        status=AnnualReportStatus.PENDING_CLIENT,
        filing_deadline=deadline,
        updated_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    annual_repo = SimpleNamespace(list_for_dashboard=lambda limit=50: [report])
    business_repo = _make_business_repo("Client X")
    notification_repo = _make_notification_repo(last=None)

    with mock.patch("app.dashboard.services._quick_actions_helpers.ClientRecordRepository"), \
         mock.patch("app.dashboard.services._quick_actions_helpers.get_full_record", return_value={"full_name": "Client X"}):
        actions = helpers.build_annual_report_actions(annual_repo, business_repo, notification_repo, today)

    assert len(actions) == 1
    assert actions[0]["key"] == "annual_report_client_reminder"
    assert actions[0]["method"] == "post"


# ── Builder ───────────────────────────────────────────────────────────────────

def test_build_quick_actions_sorted_by_category_then_urgency(monkeypatch):
    today = date(2026, 4, 28)
    binder_repo = object()
    vat_repo = object()
    annual_repo = object()
    business_repo = SimpleNamespace()
    notification_repo = object()

    monkeypatch.setattr(
        "app.dashboard.services.dashboard_quick_actions_builder.build_binder_actions",
        lambda *_: [{"key": "binder_pickup_reminder", "category": "binders", "urgency": "overdue", "due_date": "2026-03-01"}],
    )
    monkeypatch.setattr(
        "app.dashboard.services.dashboard_quick_actions_builder.build_vat_actions",
        lambda *_: [
            {"key": "vat_navigate", "category": "vat", "urgency": "overdue", "due_date": "2026-02-15"},
            {"key": "vat_navigate", "category": "vat", "urgency": "upcoming", "due_date": "2026-04-15"},
        ],
    )
    monkeypatch.setattr(
        "app.dashboard.services.dashboard_quick_actions_builder.build_annual_report_actions",
        lambda *_: [{"key": "annual_report_navigate", "category": "annual_reports", "urgency": "overdue", "due_date": "2026-03-31"}],
    )
    actions = build_quick_actions(
        binder_repo=binder_repo,
        business_repo=business_repo,
        vat_repo=vat_repo,
        annual_report_repo=annual_repo,
        notification_repo=notification_repo,
        today=today,
    )

    categories = [a["category"] for a in actions]
    assert categories == ["vat", "vat", "annual_reports", "binders"]
    assert actions[0]["urgency"] == "overdue"
    assert actions[1]["urgency"] == "upcoming"
