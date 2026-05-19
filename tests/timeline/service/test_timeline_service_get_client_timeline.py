from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.binders.models.binder import BinderStatus
from app.charge.models.charge import ChargeStatus, ChargeType
from app.core.exceptions import NotFoundError
from app.timeline.services.timeline_service import TimelineService
from tests.helpers.identity import seed_business, seed_client_identity


def _business(test_db):
    client = seed_client_identity(
        test_db,
        full_name="Timeline Service Client",
        id_number="TS100",
    )
    business = seed_business(
        test_db,
        legal_entity_id=client.legal_entity_id,
        business_name="Timeline Service Business",
        opened_at=date(2026, 1, 1),
    )
    test_db.commit()
    test_db.refresh(business)
    business.client_id = client.id
    return business


def test_get_client_timeline_sorts_events_and_applies_pagination(test_db, monkeypatch):
    service = TimelineService(test_db)
    business = _business(test_db)

    binder = SimpleNamespace(
        id=1,
        client_record_id=business.client_id,
        binder_number="TL-1",
        period_start=date(2026, 1, 1),
        returned_at=date(2026, 1, 3),
        status=BinderStatus.RETURNED,
        pickup_person_name=None,
    )
    charge = SimpleNamespace(
        id=7,
        charge_type=ChargeType.CONSULTATION_FEE,
        status=ChargeStatus.ISSUED,
        amount=Decimal("100.00"),
        created_at=datetime(2026, 1, 6, 9, 0),
        issued_at=datetime(2026, 1, 7, 9, 0),
        paid_at=datetime(2025, 12, 30, 9, 0),
    )
    invoice = SimpleNamespace(
        charge_id=7,
        created_at=datetime(2026, 1, 8, 9, 0),
        provider="Test",
        external_invoice_id="INV-1",
    )

    captured = {}

    def _list_by_client_record(client_id):
        captured["client_id"] = client_id
        return [binder]

    monkeypatch.setattr(service.binder_repo, "list_by_client_record", _list_by_client_record)
    monkeypatch.setattr(
        service,
        "_append_status_change_events",
        lambda events, _binder: events.append(
            {
                "event_type": "binder_status_change",
                "timestamp": datetime(2026, 1, 4, 9, 0),
            }
        ),
    )
    monkeypatch.setattr(service.charge_repo, "list_charges", lambda **_kwargs: [charge])
    monkeypatch.setattr(
        service.invoice_repo,
        "list_by_charge_ids",
        lambda charge_ids: [invoice] if charge_ids else [],
    )
    monkeypatch.setattr(
        service,
        "_build_annual_report_events",
        lambda _client_id: [
            {
                "event_type": "annual_report_status_changed",
                "timestamp": datetime(2026, 1, 2, 9, 0),
            }
        ],
    )
    monkeypatch.setattr(
        "app.timeline.services.timeline_service.build_client_events",
        lambda _db, _client_id, business_ids: [
            {"event_type": "client_created", "timestamp": datetime(2026, 1, 9, 9, 0)}
        ],
    )

    events, total = service.get_client_timeline(
        client_record_id=business.client_id,
        page=1,
        page_size=3,
    )

    assert captured["client_id"] == business.client_id
    assert total == 9
    assert [event["event_type"] for event in events] == [
        "client_created",
        "invoice_attached",
        "charge_issued",
    ]


def test_get_client_timeline_skips_unreceived_binder_event(test_db, monkeypatch):
    service = TimelineService(test_db)
    business = _business(test_db)

    binder = SimpleNamespace(
        id=1,
        client_record_id=business.client_id,
        binder_number="TL-EMPTY",
        period_start=None,
        returned_at=None,
        status=BinderStatus.IN_OFFICE,
        pickup_person_name=None,
    )

    monkeypatch.setattr(service.binder_repo, "list_by_client_record", lambda _client_id: [binder])
    monkeypatch.setattr(service, "_append_status_change_events", lambda _events, _binder: None)
    monkeypatch.setattr(service.charge_repo, "list_charges", lambda **_kwargs: [])
    monkeypatch.setattr(service.invoice_repo, "list_by_charge_ids", lambda _charge_ids: [])
    monkeypatch.setattr(service, "_build_annual_report_events", lambda _client_id: [])
    monkeypatch.setattr(
        "app.timeline.services.timeline_service.build_client_events",
        lambda _db, _client_id, _business_ids: [],
    )

    events, total = service.get_client_timeline(
        client_record_id=business.client_id,
        page=1,
        page_size=20,
    )

    assert events == []
    assert total == 0


def test_get_client_timeline_raises_for_missing_client(test_db):
    service = TimelineService(test_db)

    try:
        service.get_client_timeline(client_record_id=99999)
    except NotFoundError as exc:
        assert exc.code == "TIMELINE.CLIENT_NOT_FOUND"
    else:
        assert False, "Expected NotFoundError for missing client"


def test_append_status_change_events_skips_noise_and_keeps_meaningful(test_db, monkeypatch):
    service = TimelineService(test_db)
    binder = SimpleNamespace(id=17, binder_number="TL-17", status=BinderStatus.IN_OFFICE)
    events = []
    logs = [
        SimpleNamespace(
            old_status="none",
            new_status="in_office",
            changed_at=datetime(2026, 1, 1, 9, 0),
        ),
        SimpleNamespace(
            old_status="in_office",
            new_status="ready_for_pickup",
            changed_at=datetime(2026, 1, 2, 9, 0),
        ),
        SimpleNamespace(
            old_status="returned",
            new_status="returned",
            changed_at=datetime(2026, 1, 3, 9, 0),
        ),
    ]

    monkeypatch.setattr(service.status_log_repo, "list_by_binder", lambda _binder_id: logs)

    service._append_status_change_events(events, binder)

    assert [event["event_type"] for event in events] == ["binder_status_change"]
    assert events[0]["metadata"] == {
        "old_status": "in_office",
        "new_status": "ready_for_pickup",
    }


def test_append_status_change_events_handles_enum_values(test_db, monkeypatch):
    """_append_status_change_events must skip noise rows even when old_status/new_status
    are BinderStatus Enum instances (not raw strings), as may happen in tests or future
    SQLAlchemy Enum-column migrations."""
    service = TimelineService(test_db)
    binder = SimpleNamespace(id=18, binder_number="TL-18", status=BinderStatus.READY_FOR_PICKUP)
    events = []
    logs = [
        # none → in_office expressed as Enum — must be skipped
        SimpleNamespace(
            old_status=None,
            new_status=BinderStatus.IN_OFFICE,
            changed_at=datetime(2026, 2, 1, 9, 0),
        ),
        # same-status expressed as Enum — must be skipped
        SimpleNamespace(
            old_status=BinderStatus.IN_OFFICE,
            new_status=BinderStatus.IN_OFFICE,
            changed_at=datetime(2026, 2, 2, 9, 0),
        ),
        # meaningful transition — must be kept
        SimpleNamespace(
            old_status=BinderStatus.IN_OFFICE,
            new_status=BinderStatus.READY_FOR_PICKUP,
            changed_at=datetime(2026, 2, 3, 9, 0),
        ),
    ]

    monkeypatch.setattr(service.status_log_repo, "list_by_binder", lambda _binder_id: logs)

    service._append_status_change_events(events, binder)

    assert [event["event_type"] for event in events] == ["binder_status_change"]
    assert events[0]["metadata"]["old_status"] == "in_office"
    assert events[0]["metadata"]["new_status"] == "ready_for_pickup"
