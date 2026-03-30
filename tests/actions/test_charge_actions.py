from types import SimpleNamespace

from app.actions.charge_actions import get_charge_actions
from app.charge.models.charge import ChargeStatus


def test_draft_charge_cancel_confirmation_uses_unambiguous_confirm_label():
    charge = SimpleNamespace(id=20, status=ChargeStatus.DRAFT)

    actions = get_charge_actions(charge)
    cancel_action = next(action for action in actions if action["key"] == "cancel_charge")

    assert cancel_action["confirm"]["confirm_label"] == "אשר ביטול"


def test_issued_charge_returns_mark_paid_and_cancel():
    charge = SimpleNamespace(id=21, status=ChargeStatus.ISSUED)

    actions = get_charge_actions(charge)

    assert [action["key"] for action in actions] == ["mark_paid", "cancel_charge"]
