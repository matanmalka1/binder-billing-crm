from datetime import date, datetime
from types import SimpleNamespace

from app.binders.models.binder import BinderStatus
from app.charge.models.charge import ChargeStatus, ChargeType
from app.timeline.services.timeline_event_builders import (
    binder_received_event,
    binder_status_change_event,
    charge_created_event,
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
    assert event["actions"][0]["key"] == "ready"


def test_charge_created_event_includes_actions_and_metadata():
    charge = SimpleNamespace(
        id=5,
        charge_type=ChargeType.RETAINER,
        status=ChargeStatus.DRAFT,
        amount=12.5,
        created_at=datetime(2026, 3, 2, 9, 30),
    )

    event = charge_created_event(charge)

    assert event["event_type"] == "charge_created"
    assert event["timestamp"] == datetime(2026, 3, 2, 9, 30)
    assert event["description"] == "חיוב חדש: ריטיינר"
    assert event["metadata"] == {"amount": 12.5, "status": "draft"}
    assert event["actions"] == event["available_actions"]
    assert {action["key"] for action in event["actions"]} == {"issue_charge", "cancel_charge"}
