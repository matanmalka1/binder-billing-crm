def work_queue_item(binder, client, work_state, signals, reference_date) -> dict:
    return {
        "binder_id": binder.id,
        "client_id": client.id,
        "client_name": client.full_name,
        "binder_number": binder.binder_number,
        "work_state": work_state.value,
        "signals": signals,
        "days_since_received": (reference_date - binder.received_at).days,
        "expected_return_at": binder.expected_return_at,
    }


def overdue_alert_item(binder, client, days_overdue: int) -> dict:
    return {
        "binder_id": binder.id,
        "client_id": client.id,
        "client_name": client.full_name,
        "binder_number": binder.binder_number,
        "alert_type": "overdue",
        "days_overdue": days_overdue,
        "days_remaining": None,
    }


def near_sla_alert_item(binder, client, days_remaining: int) -> dict:
    return {
        "binder_id": binder.id,
        "client_id": client.id,
        "client_name": client.full_name,
        "binder_number": binder.binder_number,
        "alert_type": "near_sla",
        "days_overdue": None,
        "days_remaining": days_remaining,
    }


def idle_attention_item(binder, client, reference_date) -> dict:
    return {
        "item_type": "idle_binder",
        "binder_id": binder.id,
        "client_id": client.id,
        "client_name": client.full_name,
        "description": (
            f"Binder {binder.binder_number} idle for "
            f"{(reference_date - binder.received_at).days} days"
        ),
    }


def ready_attention_item(binder, client) -> dict:
    return {
        "item_type": "ready_for_pickup",
        "binder_id": binder.id,
        "client_id": client.id,
        "client_name": client.full_name,
        "description": f"Binder {binder.binder_number} ready for pickup",
    }


def unpaid_charge_attention_item(charge, client) -> dict:
    return {
        "item_type": "unpaid_charge",
        "binder_id": None,
        "client_id": client.id,
        "client_name": client.full_name,
        "description": f"Unpaid charge: {float(charge.amount)} {charge.currency}",
    }
