from __future__ import annotations

from typing import Any

from app.actions.action_helpers import _generate_action_id, _value, build_action
from app.binders.models.binder import Binder, BinderStatus


def get_binder_actions(binder: Binder) -> list[dict[str, Any]]:
    """Return executable actions for a binder based on its current logistics status."""
    status = _value(binder.status)
    actions: list[dict[str, Any]] = []

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
                confirm={
                    "title": "אישור סימון כמוכן לאיסוף",
                    "message": "האם לסמן את הקלסר כמוכן לאיסוף?",
                    "confirm_label": "אישור",
                    "cancel_label": "ביטול",
                },
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
                confirm={
                    "title": "ביטול סטטוס מוכן לאיסוף",
                    "message": "האם לבטל את הסימון כמוכן לאיסוף ולהחזיר את הקלסר לסטטוס במשרד?",
                    "confirm_label": "אישור",
                    "cancel_label": "ביטול",
                },
            )
        )
        actions.append(
            build_action(
                key="return",
                label="החזרת קלסר",
                method="post",
                endpoint=f"/binders/{binder.id}/return",
                action_id=_generate_action_id("binder", binder.id, "return"),
                confirm={
                    "title": "אישור החזרת קלסר",
                    "message": "אנא הזן את שם האדם שאסף את הקלסר.",
                    "confirm_label": "אישור",
                    "cancel_label": "ביטול",
                    "inputs": [
                        {
                            "name": "pickup_person_name",
                            "label": "שם האוסף",
                            "type": "text",
                            "required": True,
                        }
                    ],
                },
            )
        )

    return actions


__all__ = ["get_binder_actions"]
