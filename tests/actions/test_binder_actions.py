from types import SimpleNamespace

from app.actions.binder_actions import get_binder_actions
from app.binders.models.binder import BinderStatus


def test_in_office_binder_only_exposes_ready_action():
    binder = SimpleNamespace(id=10, status=BinderStatus.IN_OFFICE)

    actions = get_binder_actions(binder)

    assert [action["key"] for action in actions] == ["ready"]


def test_ready_for_pickup_binder_exposes_revert_and_return_with_pickup_input():
    binder = SimpleNamespace(id=11, status=BinderStatus.READY_FOR_PICKUP)

    actions = get_binder_actions(binder)

    assert [action["key"] for action in actions] == ["revert_ready", "return"]
    assert actions[1]["confirm"]["inputs"][0]["name"] == "pickup_person_name"
    assert actions[1]["confirm"]["inputs"][0]["required"] is True


def test_returned_binder_has_no_actions():
    binder = SimpleNamespace(id=12, status=BinderStatus.RETURNED)

    assert get_binder_actions(binder) == []
