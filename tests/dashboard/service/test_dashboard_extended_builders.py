from datetime import date
from types import SimpleNamespace

from app.dashboard.services.dashboard_extended_builders import (
    idle_attention_item,
    ready_attention_item,
    unpaid_charge_attention_item,
    work_queue_item,
)


def test_dashboard_extended_builders_return_expected_payload_shapes():
    reference_date = date(2026, 3, 10)
    binder = SimpleNamespace(
        id=10,
        client_id=20,
        binder_number="DB-100",
        period_start=date(2026, 3, 1),
    )
    business = SimpleNamespace(id=20, full_name="Dashboard Client")
    charge = SimpleNamespace(amount=123.45)
    work_state = SimpleNamespace(value="in_progress")
    signals = [{"key": "idle", "level": "yellow"}]

    queue = work_queue_item(binder, business, work_state, signals, reference_date)
    assert queue["binder_id"] == binder.id
    assert queue["client_name"] == business.full_name
    assert queue["work_state"] == "in_progress"
    assert queue["days_since_received"] == 9

    idle = idle_attention_item(binder, business, reference_date)
    assert idle["item_type"] == "idle_binder"
    assert "9 ימים" in idle["description"]

    ready = ready_attention_item(binder, business)
    assert ready["item_type"] == "ready_for_pickup"
    assert "מוכן לאיסוף" in ready["description"]

    unpaid = unpaid_charge_attention_item(charge, business)
    assert unpaid["item_type"] == "unpaid_charge"
    assert unpaid["description"] == "חיוב לא משולם: ₪123.45"
