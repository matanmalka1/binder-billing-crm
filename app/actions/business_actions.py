from __future__ import annotations

from typing import Optional

from app.actions.action_helpers import (
    ActionContract,
    _generate_action_id,
    _value,
    build_action,
    build_confirm,
)
from app.businesses.models.business import Business, BusinessStatus
from app.users.models.user import UserRole


def get_business_actions(
    business: Business,
    user_role: Optional[UserRole] = None,
    client_id: Optional[int] = None,
) -> list[ActionContract]:
    """Return executable actions for a business (role-aware)."""
    status = _value(business.status)
    client_id = client_id if client_id is not None else getattr(business, "client_id", None)
    if client_id is None:
        raise ValueError("Business actions require client_id for endpoint construction")
    endpoint = f"/clients/{client_id}/businesses/{business.id}"
    actions: list[ActionContract] = []

    if status == BusinessStatus.ACTIVE.value and user_role == UserRole.ADVISOR:
        actions.append(
            build_action(
                key="freeze",
                label="הקפאת עסק",
                method="patch",
                endpoint=endpoint,
                payload={"status": "frozen"},
                action_id=_generate_action_id("business", business.id, "freeze"),
                confirm=build_confirm(
                    "אישור הקפאת עסק",
                    "האם להקפיא את העסק?",
                    confirm_label="הקפאה",
                ),
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
                confirm=build_confirm(
                    "אישור סגירת עסק",
                    "האם לסגור את העסק?",
                ),
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
                    confirm=build_confirm(
                        "אישור סגירת עסק",
                        "האם לסגור את העסק?",
                    ),
                )
            )

    return actions


__all__ = ["get_business_actions"]
