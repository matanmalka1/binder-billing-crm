from __future__ import annotations

from app.actions.action_helpers import (
    ActionContract,
    _generate_action_id,
    _value,
    build_action,
    build_confirm,
)
from app.charge.models.charge import Charge, ChargeStatus
from app.users.models.user import UserRole


def _cancel_charge_action(charge_id: int) -> ActionContract:
    return build_action(
        key="cancel_charge",
        label="ביטול חיוב",
        method="post",
        endpoint=f"/charges/{charge_id}/cancel",
        action_id=_generate_action_id("charge", charge_id, "cancel_charge"),
        confirm=build_confirm(
            "אישור ביטול חיוב",
            "האם לבטל את החיוב?",
            confirm_label="אשר ביטול",
            cancel_label="חזרה",
        ),
    )


def get_charge_actions(
    charge: Charge,
    *,
    user_role: UserRole | str | None = None,
) -> list[ActionContract]:
    """Return executable actions for a charge."""
    if user_role not in (None, UserRole.ADVISOR, UserRole.ADVISOR.value):
        return []

    status = _value(charge.status)
    actions: list[ActionContract] = []

    if status == ChargeStatus.DRAFT.value:
        actions.append(
            build_action(
                key="issue_charge",
                label="הוצאת חיוב",
                method="post",
                endpoint=f"/charges/{charge.id}/issue",
                action_id=_generate_action_id("charge", charge.id, "issue_charge"),
            )
        )
        actions.append(_cancel_charge_action(charge.id))
        actions.append(
            build_action(
                key="delete_charge",
                label="מחיקת חיוב",
                method="delete",
                endpoint=f"/charges/{charge.id}",
                action_id=_generate_action_id("charge", charge.id, "delete_charge"),
                confirm=build_confirm(
                    "מחיקת חיוב",
                    "האם למחוק את החיוב?",
                    confirm_label="מחיקה",
                ),
            )
        )

    if status == ChargeStatus.ISSUED.value:
        actions.append(
            build_action(
                key="mark_paid",
                label="סימון חיוב כשולם",
                method="post",
                endpoint=f"/charges/{charge.id}/mark-paid",
                action_id=_generate_action_id("charge", charge.id, "mark_paid"),
                confirm=build_confirm(
                    "אישור סימון חיוב כשולם",
                    "האם לסמן את החיוב כשולם?",
                ),
            )
        )
        actions.append(_cancel_charge_action(charge.id))

    return actions


__all__ = ["get_charge_actions"]
