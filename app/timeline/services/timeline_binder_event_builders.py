from datetime import datetime

from app.timeline.labels import BINDER_STATUS_HE


def binder_received_event(binder) -> dict:
    received_on = getattr(binder, "received_at", None) or getattr(
        binder, "period_start"
    )
    return {
        "event_type": "binder_received",
        "timestamp": datetime.combine(received_on, datetime.min.time()),
        "binder_id": binder.id,
        "charge_id": None,
        "description": f"קלסר {binder.binder_number} התקבל",
        "metadata": {"binder_number": binder.binder_number},
    }


def binder_returned_event(binder) -> dict:
    return {
        "event_type": "binder_returned",
        "timestamp": datetime.combine(binder.returned_at, datetime.min.time()),
        "binder_id": binder.id,
        "charge_id": None,
        "description": f"קלסר {binder.binder_number} הוחזר",
        "metadata": {
            "binder_number": binder.binder_number,
            "pickup_person_name": binder.pickup_person_name,
        },
    }


def binder_status_change_event(binder, status_log) -> dict:
    if status_log.old_status == "none":
        description = f"קלסר {binder.binder_number} הגיע למשרד"
    else:
        description = (
            f"קלסר {binder.binder_number}: "
            f"{BINDER_STATUS_HE.get(status_log.old_status, 'סטטוס לא ידוע')} "
            f"← {BINDER_STATUS_HE.get(status_log.new_status, 'סטטוס לא ידוע')}"
        )
    return {
        "event_type": "binder_status_change",
        "timestamp": status_log.changed_at,
        "binder_id": binder.id,
        "charge_id": None,
        "description": description,
        "metadata": {
            "old_status": status_log.old_status,
            "new_status": status_log.new_status,
        },
    }
