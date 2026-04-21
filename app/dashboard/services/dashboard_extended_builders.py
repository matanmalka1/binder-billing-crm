from decimal import Decimal


def _format_ils_amount(amount) -> str:
    normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    formatted = f"{normalized:,.2f}".rstrip("0").rstrip(".")
    return f"₪{formatted}"


def ready_attention_item(binder, client) -> dict:
    return {
        "item_type": "ready_for_pickup",
        "binder_id": binder.id,
        "client_id": binder.client_record_id,
        "business_id": client.id,
        "client_name": client.full_name,
        "description": f"תיק {binder.binder_number} מוכן לאיסוף",
    }


def unpaid_charge_attention_item(charge, client) -> dict:
    return {
        "item_type": "unpaid_charge",
        "binder_id": None,
        "client_id": charge.client_record_id,
        "business_id": client.id,
        "client_name": client.full_name,
        "description": f"חיוב לא משולם: {_format_ils_amount(charge.amount)}",
    }
