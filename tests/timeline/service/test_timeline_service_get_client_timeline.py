from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.binders.models.binder import BinderStatus
from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client
from app.charge.models.charge import ChargeStatus, ChargeType
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.core.exceptions import NotFoundError
from app.timeline.services.timeline_service import TimelineService


def _business(test_db) -> Business:
    client = Client(full_name="Timeline Service Client", id_number="TS100")
    test_db.add(client)
    test_db.flush()

    business = Business(
        client_id=client.id,
        business_name="Timeline Service Business",
        business_type=BusinessType.COMPANY,
        opened_at=date(2026, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_get_client_timeline_sorts_events_and_applies_pagination(test_db, monkeypatch):
    service = TimelineService(test_db)
    business = _business(test_db)

    binder = SimpleNamespace(
        id=1,
        client_id=business.client_id,
        binder_number="TL-1",
        period_start=date(2026, 1, 1),
        returned_at=date(2026, 1, 3),
        status=BinderStatus.RETURNED,
        pickup_person_name=None,
    )
    notification = SimpleNamespace(
        created_at=datetime(2026, 1, 5, 9, 0),
        binder_id=binder.id,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        channel=NotificationChannel.EMAIL,
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

    def _list_by_client(client_id):
        captured["client_id"] = client_id
        return [binder]

    monkeypatch.setattr(service.binder_repo, "list_by_client", _list_by_client)
    monkeypatch.setattr(
        service,
        "_append_status_change_events",
        lambda events, binder: events.append(
            {
                "event_type": "binder_status_change",
                "timestamp": datetime(2026, 1, 4, 9, 0),
            }
        ),
    )
    monkeypatch.setattr(
        service.notification_repo,
        "list_by_business",
        lambda business_id, page, page_size: [notification],
    )
    monkeypatch.setattr(service.charge_repo, "list_charges", lambda **kwargs: [charge])
    monkeypatch.setattr(
        service.invoice_repo,
        "list_by_charge_ids",
        lambda charge_ids: [invoice] if charge_ids else [],
    )
    monkeypatch.setattr(
        service,
        "_build_tax_deadline_events",
        lambda client_id, business_ids: [
            {"event_type": "tax_deadline_due", "timestamp": datetime(2025, 12, 31, 9, 0)}
        ],
    )
    monkeypatch.setattr(
        service,
        "_build_annual_report_events",
        lambda client_id: [
            {
                "event_type": "annual_report_status_changed",
                "timestamp": datetime(2026, 1, 2, 9, 0),
            }
        ],
    )
    monkeypatch.setattr(
        "app.timeline.services.timeline_service.build_client_events",
        lambda db, client_id, business_ids, reminder_repo, sig_repo: [
            {"event_type": "client_created", "timestamp": datetime(2026, 1, 9, 9, 0)}
        ],
    )

    events, total = service.get_client_timeline(
        client_id=business.client_id,
        page=1,
        page_size=3,
    )

    assert captured["client_id"] == business.client_id
    assert total == 12
    assert [event["event_type"] for event in events] == [
        "client_created",
        "invoice_attached",
        "charge_issued",
    ]


def test_get_client_timeline_raises_for_missing_client(test_db):
    service = TimelineService(test_db)

    try:
        service.get_client_timeline(client_id=99999)
    except NotFoundError as exc:
        assert exc.code == "TIMELINE.CLIENT_NOT_FOUND"
    else:
        assert False, "Expected NotFoundError for missing client"


def test_append_status_change_events_appends_each_status_log(test_db, monkeypatch):
    service = TimelineService(test_db)
    binder = SimpleNamespace(id=17, binder_number="TL-17", status=BinderStatus.IN_OFFICE)
    events = []
    logs = [
        SimpleNamespace(old_status="none", new_status="in_office", changed_at=datetime(2026, 1, 1, 9, 0)),
        SimpleNamespace(old_status="in_office", new_status="ready_for_pickup", changed_at=datetime(2026, 1, 2, 9, 0)),
    ]

    monkeypatch.setattr(service.status_log_repo, "list_by_binder", lambda binder_id: logs)

    service._append_status_change_events(events, binder)

    assert [event["event_type"] for event in events] == [
        "binder_status_change",
        "binder_status_change",
    ]
