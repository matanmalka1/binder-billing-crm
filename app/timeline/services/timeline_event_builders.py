from datetime import datetime

from app.actions.action_contracts import get_binder_actions, get_charge_actions


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
            "description": f"Binder {binder.binder_number} received",
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
            "description": f"Binder {binder.binder_number} returned",
            "metadata": {
                "binder_number": binder.binder_number,
                "pickup_person_name": binder.pickup_person_name,
            },
        },
        [],
    )


def binder_status_change_event(binder, status_log) -> dict:
    actions = get_binder_actions(binder)
    return _attach_actions(
        {
            "event_type": "binder_status_change",
            "timestamp": status_log.changed_at,
            "binder_id": binder.id,
            "charge_id": None,
            "description": (
                f"Binder {binder.binder_number}: "
                f"{status_log.old_status} → {status_log.new_status}"
            ),
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
            "description": f"Notification: {notification.trigger.value}",
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
            "description": f"Charge created: {charge.charge_type.value}",
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
            "description": f"Charge issued: {charge.charge_type.value}",
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
            "description": f"Charge paid: {charge.charge_type.value}",
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
            "description": f"Invoice attached: {invoice.external_invoice_id}",
            "metadata": {
                "provider": invoice.provider,
                "external_invoice_id": invoice.external_invoice_id,
            },
        },
        [],
    )
