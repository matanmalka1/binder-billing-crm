from datetime import datetime
from types import SimpleNamespace

from app.charge.models.charge import ChargeStatus, ChargeType
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.timeline.services.timeline_binder_event_builders import (
    notification_sent_event,
)
from app.timeline.services.timeline_charge_event_builders import charge_issued_event


def test_notification_sent_event_includes_trigger_and_channel_metadata():
    notification = SimpleNamespace(
        created_at=datetime(2026, 3, 8, 10, 0),
        binder_id=44,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        channel=NotificationChannel.EMAIL,
    )

    event = notification_sent_event(notification)

    assert event["event_type"] == "notification_sent"
    assert event["timestamp"] == datetime(2026, 3, 8, 10, 0)
    assert event["binder_id"] == 44
    assert event["metadata"] == {"trigger": "binder_received", "channel": "email"}
    assert event["actions"] == event["available_actions"] == []


def test_charge_issued_event_includes_available_charge_actions():
    charge = SimpleNamespace(
        id=91,
        issued_at=datetime(2026, 3, 9, 9, 15),
        charge_type=ChargeType.CONSULTATION_FEE,
        status=ChargeStatus.ISSUED,
        amount=320.0,
    )

    event = charge_issued_event(charge)

    assert event["event_type"] == "charge_issued"
    assert event["timestamp"] == datetime(2026, 3, 9, 9, 15)
    assert event["metadata"] == {"amount": 320.0}
    assert event["actions"] == event["available_actions"]
    assert {action["key"] for action in event["actions"]} == {"mark_paid", "cancel_charge"}
    mark_paid_action = next(action for action in event["actions"] if action["key"] == "mark_paid")
    assert mark_paid_action["confirm"] is not None
    assert mark_paid_action["confirm"]["title"] == "אישור סימון חיוב כשולם"
