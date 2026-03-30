from types import SimpleNamespace

from app.actions.action_contracts import (
    build_action,
    get_binder_actions,
    get_business_actions,
    get_charge_actions,
)
from app.binders.models.binder import BinderStatus
from app.businesses.models.business import BusinessStatus
from app.charge.models.charge import ChargeStatus
from app.users.models.user import UserRole


def test_get_binder_actions_in_office_returns_ready_action():
    binder = SimpleNamespace(id=10, status=BinderStatus.IN_OFFICE)

    actions = get_binder_actions(binder)

    assert len(actions) == 1
    assert actions[0]["key"] == "ready"
    assert actions[0]["id"] == "binder-10-ready"
    assert actions[0]["endpoint"] == "/binders/10/ready"


def test_get_binder_actions_ready_for_pickup_returns_return_action_with_input():
    binder = SimpleNamespace(id=11, status=BinderStatus.READY_FOR_PICKUP)

    actions = get_binder_actions(binder)

    assert len(actions) == 2
    assert [action["key"] for action in actions] == ["revert_ready", "return"]
    assert actions[1]["id"] == "binder-11-return"
    assert actions[1]["confirm"]["inputs"][0]["name"] == "pickup_person_name"


def test_get_business_actions_active_advisor_returns_freeze_action():
    business = SimpleNamespace(id=5, status=BusinessStatus.ACTIVE)

    actions = get_business_actions(business, user_role=UserRole.ADVISOR)

    assert len(actions) == 1
    assert actions[0]["key"] == "freeze"
    assert actions[0]["payload"] == {"status": "frozen"}
    assert actions[0]["id"] == "business-5-freeze"


def test_get_business_actions_active_secretary_returns_no_actions():
    business = SimpleNamespace(id=6, status=BusinessStatus.ACTIVE)

    actions = get_business_actions(business, user_role=UserRole.SECRETARY)

    assert actions == []


def test_get_business_actions_frozen_returns_activate_action():
    business = SimpleNamespace(id=7, status=BusinessStatus.FROZEN)

    actions = get_business_actions(business, user_role=UserRole.ADVISOR)

    assert len(actions) == 1
    assert actions[0]["key"] == "activate"
    assert actions[0]["payload"] == {"status": "active"}
    assert actions[0]["id"] == "business-7-activate"


def test_get_charge_actions_draft_returns_issue_and_cancel():
    charge = SimpleNamespace(id=20, status=ChargeStatus.DRAFT)

    actions = get_charge_actions(charge)

    keys = [action["key"] for action in actions]
    assert keys == ["issue_charge", "cancel_charge"]
    assert actions[0]["id"] == "charge-20-issue_charge"
    assert actions[1]["id"] == "charge-20-cancel_charge"


def test_get_charge_actions_issued_returns_mark_paid_and_cancel():
    charge = SimpleNamespace(id=21, status=ChargeStatus.ISSUED)

    actions = get_charge_actions(charge)

    keys = [action["key"] for action in actions]
    assert keys == ["mark_paid", "cancel_charge"]
    assert actions[0]["id"] == "charge-21-mark_paid"
    assert actions[1]["id"] == "charge-21-cancel_charge"


def test_build_action_omits_optional_keys_when_none():
    action = build_action(
        key="k",
        label="l",
        method="post",
        endpoint="/e",
        action_id="id-1",
    )

    assert action == {
        "id": "id-1",
        "key": "k",
        "label": "l",
        "method": "post",
        "endpoint": "/e",
    }
