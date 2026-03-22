from datetime import date, datetime
from types import SimpleNamespace

from app.binders.models.binder import BinderStatus
from app.charge.models.charge import ChargeStatus, ChargeType
from app.timeline.services.timeline_binder_event_builders import (
    binder_received_event,
    binder_returned_event,
    binder_status_change_event,
)
from app.timeline.services.timeline_charge_event_builders import (
    charge_created_event,
    charge_paid_event,
    invoice_attached_event,
)


def test_binder_status_change_event_for_new_binder():
    binder = SimpleNamespace(
        id=11,
        binder_number="B-123",
        status=BinderStatus.IN_OFFICE,
    )
    status_log = SimpleNamespace(
        old_status="none",
        new_status="in_office",
        changed_at=datetime(2026, 3, 1, 10, 0),
    )

    event = binder_status_change_event(binder, status_log)

    assert event["event_type"] == "binder_status_change"
    assert event["timestamp"] == datetime(2026, 3, 1, 10, 0)
    assert event["description"] == "קלסר B-123 הגיע למשרד"
    assert event["metadata"] == {"old_status": "none", "new_status": "in_office"}
    assert event["actions"] == event["available_actions"]
    assert event["actions"][0]["endpoint"] == "/binders/11/ready"


def test_binder_status_change_event_for_regular_transition():
    binder = SimpleNamespace(
        id=12,
        binder_number="B-124",
        status=BinderStatus.READY_FOR_PICKUP,
    )
    status_log = SimpleNamespace(
        old_status="in_office",
        new_status="ready_for_pickup",
        changed_at=datetime(2026, 3, 2, 11, 0),
    )

    event = binder_status_change_event(binder, status_log)

    assert event["description"] == "קלסר B-124: במשרד ← מוכן לאיסוף"
    assert event["metadata"] == {
        "old_status": "in_office",
        "new_status": "ready_for_pickup",
    }


def test_binder_received_event_attaches_ready_action_and_metadata():
    binder = SimpleNamespace(
        id=9,
        binder_number="C-777",
        received_at=date(2026, 2, 15),
        status=BinderStatus.IN_OFFICE,
    )

    event = binder_received_event(binder)

    assert event["event_type"] == "binder_received"
    assert event["timestamp"] == datetime(2026, 2, 15)
    assert event["metadata"] == {"binder_number": "C-777"}
    assert event["actions"] == event["available_actions"]
    ready_action = event["actions"][0]
    assert ready_action["key"] == "ready"
    assert ready_action["confirm"] is not None
    assert ready_action["confirm"]["title"] == "אישור סימון כמוכן לאיסוף"


def test_charge_created_event_includes_actions_and_metadata():
    charge = SimpleNamespace(
        id=5,
        charge_type=ChargeType.MONTHLY_RETAINER,
        status=ChargeStatus.DRAFT,
        amount=12.5,
        created_at=datetime(2026, 3, 2, 9, 30),
    )

    event = charge_created_event(charge)

    assert event["event_type"] == "charge_created"
    assert event["timestamp"] == datetime(2026, 3, 2, 9, 30)
    assert event["description"] == "חיוב חדש: ריטיינר חודשי"
    assert event["metadata"] == {"amount": 12.5, "status": "draft"}
    assert event["actions"] == event["available_actions"]
    assert {action["key"] for action in event["actions"]} == {"issue_charge", "cancel_charge"}


def test_binder_returned_event_includes_pickup_person_metadata():
    binder = SimpleNamespace(
        id=10,
        binder_number="D-404",
        returned_at=date(2026, 3, 3),
        pickup_person_name="Dana",
    )

    event = binder_returned_event(binder)

    assert event["event_type"] == "binder_returned"
    assert event["timestamp"] == datetime(2026, 3, 3)
    assert event["metadata"] == {
        "binder_number": "D-404",
        "pickup_person_name": "Dana",
    }
    assert event["actions"] == event["available_actions"] == []


def test_charge_paid_event_is_actionless_and_formats_amount():
    charge = SimpleNamespace(
        id=6,
        charge_type=ChargeType.MONTHLY_RETAINER,
        status=ChargeStatus.PAID,
        amount=200.75,
        paid_at=datetime(2026, 3, 4, 15, 45),
    )

    event = charge_paid_event(charge)

    assert event["event_type"] == "charge_paid"
    assert event["timestamp"] == datetime(2026, 3, 4, 15, 45)
    assert event["description"] == "חיוב שולם: ריטיינר חודשי"
    assert event["metadata"] == {"amount": 200.75}
    assert event["actions"] == event["available_actions"] == []


def test_invoice_attached_event_includes_provider_metadata():
    charge = SimpleNamespace(id=7)
    invoice = SimpleNamespace(
        created_at=datetime(2026, 3, 5, 8, 0),
        provider="Stripe",
        external_invoice_id="INV-1001",
    )

    event = invoice_attached_event(charge, invoice)

    assert event["event_type"] == "invoice_attached"
    assert event["timestamp"] == datetime(2026, 3, 5, 8, 0)
    assert event["description"] == "חשבונית צורפה: INV-1001"
    assert event["metadata"] == {
        "provider": "Stripe",
        "external_invoice_id": "INV-1001",
    }
    assert event["actions"] == event["available_actions"] == []
