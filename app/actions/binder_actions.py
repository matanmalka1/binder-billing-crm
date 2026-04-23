from __future__ import annotations

from app.actions.action_helpers import (
    ActionContract,
    _generate_action_id,
    _value,
    build_action,
    build_confirm,
)
from app.binders.models.binder import Binder, BinderStatus


def get_binder_actions(binder: Binder) -> list[ActionContract]:
    """Return executable actions for a binder based on its current logistics status."""
    status = _value(binder.status)
    actions: list[ActionContract] = []

    if status in {
        BinderStatus.IN_OFFICE.value,
        BinderStatus.CLOSED_IN_OFFICE.value,
    }:
        actions.append(
            build_action(
                key="ready",
                label="מוכן לאיסוף",
                method="post",
                endpoint=f"/binders/{binder.id}/ready",
                action_id=_generate_action_id("binder", binder.id, "ready"),
                confirm=build_confirm(
                    "אישור סימון כמוכן לאיסוף",
                    "האם לסמן את הקלסר כמוכן לאיסוף?",
                ),
            )
        )

    if status == BinderStatus.READY_FOR_PICKUP.value:
        actions.append(
            build_action(
                key="revert_ready",
                label="בטל מוכן לאיסוף",
                method="post",
                endpoint=f"/binders/{binder.id}/revert-ready",
                action_id=_generate_action_id("binder", binder.id, "revert_ready"),
                confirm=build_confirm(
                    "ביטול סטטוס מוכן לאיסוף",
                    "האם לבטל את הסימון כמוכן לאיסוף ולהחזיר את הקלסר לסטטוס במשרד?",
                ),
            )
        )
        actions.append(
            build_action(
                key="return",
                label="החזרת קלסר",
                method="post",
                endpoint=f"/binders/{binder.id}/return",
                action_id=_generate_action_id("binder", binder.id, "return"),
                confirm=build_confirm(
                    "אישור החזרת קלסר",
                    "אנא הזן את שם האדם שאסף את הקלסר.",
                    inputs=[
                        {
                            "name": "pickup_person_name",
                            "label": "שם האוסף",
                            "type": "text",
                            "required": True,
                        }
                    ],
                ),
            )
        )

    return actions


__all__ = ["get_binder_actions"]
