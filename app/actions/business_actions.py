from __future__ import annotations

from typing import Any, Optional

from app.actions.action_helpers import _generate_action_id, _value, build_action
from app.businesses.models.business import Business, BusinessStatus
from app.users.models.user import UserRole


def get_business_actions(
    business: Business,
    user_role: Optional[UserRole] = None,
) -> list[dict[str, Any]]:
    """Return executable actions for a business (role-aware)."""
    status = _value(business.status)
    # TODO: migrate to /client-records/{business.legal_entity_id}/businesses/{business.id}
    # once frontend routing is updated — breaking change, coordinate with UI team.
    endpoint = f"/clients/{business.client_id}/businesses/{business.id}"
    actions: list[dict[str, Any]] = []

    if status == BusinessStatus.ACTIVE.value and user_role == UserRole.ADVISOR:
        actions.append(
            build_action(
                key="freeze",
                label="הקפאת עסק",
                method="patch",
                endpoint=endpoint,
                payload={"status": "frozen"},
                action_id=_generate_action_id("business", business.id, "freeze"),
                confirm={
                    "title": "אישור הקפאת עסק",
                    "message": "האם להקפיא את העסק?",
                    "confirm_label": "הקפאה",
                    "cancel_label": "ביטול",
                },
            )
        )
        actions.append(
            build_action(
                key="close",
                label="סגירת עסק",
                method="patch",
                endpoint=endpoint,
                payload={"status": "closed"},
                action_id=_generate_action_id("business", business.id, "close"),
                confirm={
                    "title": "אישור סגירת עסק",
                    "message": "האם לסגור את העסק?",
                    "confirm_label": "אישור",
                    "cancel_label": "ביטול",
                },
            )
        )

    if status == BusinessStatus.FROZEN.value:
        actions.append(
            build_action(
                key="activate",
                label="הפעלת עסק",
                method="patch",
                endpoint=endpoint,
                payload={"status": "active"},
                action_id=_generate_action_id("business", business.id, "activate"),
            )
        )
        if user_role == UserRole.ADVISOR:
            actions.append(
                build_action(
                    key="close",
                    label="סגירת עסק",
                    method="patch",
                    endpoint=endpoint,
                    payload={"status": "closed"},
                    action_id=_generate_action_id("business", business.id, "close"),
                    confirm={
                        "title": "אישור סגירת עסק",
                        "message": "האם לסגור את העסק?",
                        "confirm_label": "אישור",
                        "cancel_label": "ביטול",
                    },
                )
            )

    return actions


__all__ = ["get_business_actions"]
