from __future__ import annotations

from app.binders.models.binder import Binder, BinderStatus
from app.core.action_builders import mutation_action
from app.core.action_schemas import ActionDescriptor


def get_binder_actions(binder: Binder) -> list[ActionDescriptor]:
    """Return executable actions for a binder based on its current logistics status."""
    status = binder.status
    actions: list[ActionDescriptor] = []

    if status in {
        BinderStatus.IN_OFFICE,
        BinderStatus.CLOSED_IN_OFFICE,
    }:
        actions.append(
            mutation_action(
                key="ready",
                label="מוכן לאיסוף",
                endpoint=f"/binders/{binder.id}/ready",
                confirm_title="אישור סימון כמוכן לאיסוף",
                confirm_message="האם לסמן את הקלסר כמוכן לאיסוף?",
            )
        )

    if status == BinderStatus.READY_FOR_PICKUP:
        actions.append(
            mutation_action(
                key="revert_ready",
                label="בטל מוכן לאיסוף",
                endpoint=f"/binders/{binder.id}/revert-ready",
                confirm_title="ביטול סטטוס מוכן לאיסוף",
                confirm_message="האם לבטל את הסימון כמוכן לאיסוף ולהחזיר את הקלסר לסטטוס במשרד?",
            )
        )
        actions.append(
            mutation_action(
                key="return",
                label="החזרת קלסר",
                endpoint=f"/binders/{binder.id}/return",
                confirm_title="אישור החזרת קלסר",
                confirm_message="אנא הזן את שם האדם שאסף את הקלסר.",
                payload_schema="requires_input",
            )
        )

    return actions


__all__ = ["get_binder_actions"]
