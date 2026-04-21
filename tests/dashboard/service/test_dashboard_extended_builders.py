from datetime import date
from types import SimpleNamespace

from app.dashboard.services.dashboard_extended_builders import (
    ready_attention_item,
    unpaid_charge_attention_item,
)


def test_dashboard_extended_builders_return_expected_payload_shapes():
    binder = SimpleNamespace(
        id=10,
        client_record_id=20,
        binder_number="DB-100",
        period_start=date(2026, 3, 1),
    )
    business = SimpleNamespace(id=20, full_name="Dashboard Client")
    charge = SimpleNamespace(client_record_id=20, amount=123.45)
    ready = ready_attention_item(binder, business)
    assert ready["item_type"] == "ready_for_pickup"
    assert "מוכן לאיסוף" in ready["description"]

    unpaid = unpaid_charge_attention_item(charge, business)
    assert unpaid["item_type"] == "unpaid_charge"
    assert unpaid["description"] == "חיוב לא משולם: ₪123.45"
