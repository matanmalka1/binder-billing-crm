from datetime import datetime

from app.actions.action_contracts import get_binder_actions
from app.timeline.labels import BINDER_STATUS_HE, NOTIFICATION_TRIGGER_HE


def _attach_actions(event: dict, actions: list) -> dict:
    """
    Attach actions to the event payload.

    `available_actions` is kept for backward compatibility with older clients
    that read that key; both keys intentionally reference the same list.
    """
    event["actions"] = actions
    event["available_actions"] = actions
    return event


def binder_received_event(binder) -> dict:
    actions = get_binder_actions(binder)
    received_on = getattr(binder, "received_at", None) or getattr(binder, "period_start")
    return _attach_actions(
        {
            "event_type": "binder_received",
            "timestamp": datetime.combine(received_on, datetime.min.time()),
            "binder_id": binder.id,
            "charge_id": None,
            "description": f"קלסר {binder.binder_number} התקבל",
            "metadata": {"binder_number": binder.binder_number},
        },
        actions,
    )


def binder_returned_event(binder) -> dict:
    return _attach_actions(
        {
            "event_type": "binder_returned",
            "timestamp": datetime.combine(binder.returned_at, datetime.min.time()),
            "binder_id": binder.id,
            "charge_id": None,
            "description": f"קלסר {binder.binder_number} הוחזר",
            "metadata": {
                "binder_number": binder.binder_number,
                "pickup_person_name": binder.pickup_person_name,
            },
        },
        [],
    )


def binder_status_change_event(binder, status_log) -> dict:
    actions = get_binder_actions(binder)
    if status_log.old_status == "none":
        description = f"קלסר {binder.binder_number} הגיע למשרד"
    else:
        description = (
            f"קלסר {binder.binder_number}: "
            f"{BINDER_STATUS_HE.get(status_log.old_status, 'סטטוס לא ידוע')} "
            f"← {BINDER_STATUS_HE.get(status_log.new_status, 'סטטוס לא ידוע')}"
        )
    return _attach_actions(
        {
            "event_type": "binder_status_change",
            "timestamp": status_log.changed_at,
            "binder_id": binder.id,
            "charge_id": None,
            "description": description,
            "metadata": {
                "old_status": status_log.old_status,
                "new_status": status_log.new_status,
            },
        },
        actions,
    )


def notification_sent_event(notification) -> dict:
    return _attach_actions(
        {
            "event_type": "notification_sent",
            "timestamp": notification.created_at,
            "binder_id": notification.binder_id,
            "charge_id": None,
            "description": f"התראה: {NOTIFICATION_TRIGGER_HE.get(notification.trigger.value, 'סוג לא ידוע')}",
            "metadata": {
                "trigger": notification.trigger.value,
                "channel": notification.channel.value,
            },
        },
        [],
    )
