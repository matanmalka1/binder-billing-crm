from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.binders.models.binder import BinderStatus, BinderType
from app.charge.models.charge import ChargeStatus, ChargeType
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.timeline.services.timeline_service import TimelineService


def test_get_client_timeline_sorts_events_and_applies_pagination(test_db, monkeypatch):
    service = TimelineService(test_db)
    binder = SimpleNamespace(
        id=1,
        client_id=100,
        binder_number="TL-1",
        binder_type=BinderType.VAT,
        received_at=date(2026, 1, 1),
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
        charge_type=ChargeType.ONE_TIME,
        status=ChargeStatus.ISSUED,
        amount=Decimal("100.00"),
        created_at=datetime(2026, 1, 6, 9, 0),
        issued_at=datetime(2026, 1, 7, 9, 0),
        paid_at=None,
    )
    invoice = SimpleNamespace(
        charge_id=7,
        created_at=datetime(2026, 1, 8, 9, 0),
        provider="Test",
        external_invoice_id="INV-1",
    )

    monkeypatch.setattr(service.binder_repo, "list_by_client", lambda client_id: [binder])
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
    monkeypatch.setattr(service.notification_repo, "list_by_client", lambda client_id, page, page_size: [notification])
    monkeypatch.setattr(service.charge_repo, "list_charges", lambda **kwargs: [charge])
    monkeypatch.setattr(service.invoice_repo, "list_by_charge_ids", lambda charge_ids: [invoice] if charge_ids else [])
    monkeypatch.setattr(
        service,
        "_build_tax_deadline_events",
        lambda client_id: [{"event_type": "tax_deadline_due", "timestamp": datetime(2025, 12, 31, 9, 0)}],
    )
    monkeypatch.setattr(
        service,
        "_build_annual_report_events",
        lambda client_id: [{"event_type": "annual_report_status_changed", "timestamp": datetime(2026, 1, 2, 9, 0)}],
    )
    monkeypatch.setattr(
        "app.timeline.services.timeline_service.build_client_events",
        lambda db, client_id, reminder_repo, sig_repo: [
            {"event_type": "client_created", "timestamp": datetime(2026, 1, 9, 9, 0)}
        ],
    )

    events, total = service.get_client_timeline(client_id=100, page=1, page_size=3)

    assert total == 10
    assert [event["event_type"] for event in events] == [
        "client_created",
        "invoice_attached",
        "charge_issued",
    ]
