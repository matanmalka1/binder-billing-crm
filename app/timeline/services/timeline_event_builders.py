from datetime import datetime

from app.actions.action_contracts import get_binder_actions, get_charge_actions


BINDER_STATUS_HE = {
    "none": "חדש",
    "in_office": "במשרד",
    "sent": "נשלח",
    "ready_for_pickup": "מוכן לאיסוף",
    "returned": "הוחזר",
}

CHARGE_TYPE_HE = {
    "retainer": "ריטיינר",
    "one_time": "חד פעמי",
    "hourly": "שעתי",
}

NOTIFICATION_TRIGGER_HE = {
    "binder_ready": "קלסר מוכן לאיסוף",
    "binder_overdue": "קלסר באיחור",
    "charge_due": "חיוב לתשלום",
    "binder_received": "קלסר התקבל",
}


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
    return _attach_actions(
        {
            "event_type": "binder_received",
            "timestamp": datetime.combine(binder.received_at, datetime.min.time()),
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
            f"{BINDER_STATUS_HE.get(status_log.old_status, status_log.old_status)} "
            f"← {BINDER_STATUS_HE.get(status_log.new_status, status_log.new_status)}"
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
            "description": f"התראה: {NOTIFICATION_TRIGGER_HE.get(notification.trigger.value, notification.trigger.value)}",
            "metadata": {
                "trigger": notification.trigger.value,
                "channel": notification.channel.value,
            },
        },
        [],
    )


def charge_created_event(charge) -> dict:
    actions = get_charge_actions(charge)
    return _attach_actions(
        {
            "event_type": "charge_created",
            "timestamp": charge.created_at,
            "binder_id": None,
            "charge_id": charge.id,
            "description": f"חיוב חדש: {CHARGE_TYPE_HE.get(charge.charge_type.value, charge.charge_type.value)}",
            "metadata": {
                "amount": float(charge.amount),
                "status": charge.status.value,
            },
        },
        actions,
    )


def charge_issued_event(charge) -> dict:
    actions = get_charge_actions(charge)
    return _attach_actions(
        {
            "event_type": "charge_issued",
            "timestamp": charge.issued_at,
            "binder_id": None,
            "charge_id": charge.id,
            "description": f"חיוב הונפק: {CHARGE_TYPE_HE.get(charge.charge_type.value, charge.charge_type.value)}",
            "metadata": {"amount": float(charge.amount)},
        },
        actions,
    )


def charge_paid_event(charge) -> dict:
    return _attach_actions(
        {
            "event_type": "charge_paid",
            "timestamp": charge.paid_at,
            "binder_id": None,
            "charge_id": charge.id,
            "description": f"חיוב שולם: {CHARGE_TYPE_HE.get(charge.charge_type.value, charge.charge_type.value)}",
            "metadata": {"amount": float(charge.amount)},
        },
        [],
    )


def invoice_attached_event(charge, invoice) -> dict:
    return _attach_actions(
        {
            "event_type": "invoice_attached",
            "timestamp": invoice.created_at,
            "binder_id": None,
            "charge_id": charge.id,
            "description": f"חשבונית צורפה: {invoice.external_invoice_id}",
            "metadata": {
                "provider": invoice.provider,
                "external_invoice_id": invoice.external_invoice_id,
            },
        },
        [],
    )
