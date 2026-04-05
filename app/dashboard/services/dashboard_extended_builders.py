from decimal import Decimal


def _format_ils_amount(amount) -> str:
    normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    formatted = f"{normalized:,.2f}".rstrip("0").rstrip(".")
    return f"₪{formatted}"


def work_queue_item(binder, client, reference_date) -> dict:
    return {
        "binder_id": binder.id,
        "client_id": client.client_id,
        "business_id": client.id,
        "client_name": client.full_name,
        "binder_number": binder.binder_number,
        "days_since_received": (reference_date - binder.period_start).days,
    }


def idle_attention_item(binder, client, reference_date) -> dict:
    return {
        "item_type": "idle_binder",
        "binder_id": binder.id,
        "client_id": client.client_id,
        "business_id": client.id,
        "client_name": client.full_name,
        "description": (
            f"תיק {binder.binder_number} ממתין ללא פעילות "
            f"{(reference_date - binder.period_start).days} ימים"
        ),
    }


def ready_attention_item(binder, client) -> dict:
    return {
        "item_type": "ready_for_pickup",
        "binder_id": binder.id,
        "client_id": client.client_id,
        "business_id": client.id,
        "client_name": client.full_name,
        "description": f"תיק {binder.binder_number} מוכן לאיסוף",
    }


def unpaid_charge_attention_item(charge, client) -> dict:
    return {
        "item_type": "unpaid_charge",
        "binder_id": None,
        "client_id": client.client_id,
        "business_id": client.id,
        "client_name": client.full_name,
        "description": f"חיוב לא משולם: {_format_ils_amount(charge.amount)}",
    }
