from types import SimpleNamespace

from app.actions.charge_actions import get_charge_actions
from app.charge.models.charge import ChargeStatus
from app.users.models.user import UserRole


def test_draft_charge_cancel_confirmation_uses_unambiguous_confirm_label():
    charge = SimpleNamespace(id=20, status=ChargeStatus.DRAFT)

    actions = get_charge_actions(charge)
    cancel_action = next(action for action in actions if action["key"] == "cancel_charge")

    assert cancel_action["confirm"]["confirm_label"] == "אשר ביטול"


def test_draft_charge_includes_delete_action():
    charge = SimpleNamespace(id=20, status=ChargeStatus.DRAFT)

    actions = get_charge_actions(charge)

    assert [action["key"] for action in actions] == [
        "issue_charge",
        "cancel_charge",
        "delete_charge",
    ]


def test_secretary_charge_actions_are_empty():
    charge = SimpleNamespace(id=22, status=ChargeStatus.DRAFT)

    assert get_charge_actions(charge, user_role=UserRole.SECRETARY) == []


def test_issued_charge_returns_mark_paid_and_cancel():
    charge = SimpleNamespace(id=21, status=ChargeStatus.ISSUED)

    actions = get_charge_actions(charge)

    assert [action["key"] for action in actions] == ["mark_paid", "cancel_charge"]
