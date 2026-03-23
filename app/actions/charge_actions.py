from __future__ import annotations

from typing import Any

from app.actions.action_helpers import _generate_action_id, _value, build_action
from app.charge.models.charge import Charge, ChargeStatus


def _cancel_charge_action(charge_id: int) -> dict[str, Any]:
    return build_action(
        key="cancel_charge",
        label="ביטול חיוב",
        method="post",
        endpoint=f"/charges/{charge_id}/cancel",
        action_id=_generate_action_id("charge", charge_id, "cancel_charge"),
        confirm={
            "title": "אישור ביטול חיוב",
            "message": "האם לבטל את החיוב?",
            "confirm_label": "ביטול",
            "cancel_label": "חזרה",
        },
    )


def get_charge_actions(charge: Charge) -> list[dict[str, Any]]:
    """Return executable actions for a charge."""
    status = _value(charge.status)
    actions: list[dict[str, Any]] = []

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

    if status == ChargeStatus.ISSUED.value:
        actions.append(
            build_action(
                key="mark_paid",
                label="סימון חיוב כשולם",
                method="post",
                endpoint=f"/charges/{charge.id}/mark-paid",
                action_id=_generate_action_id("charge", charge.id, "mark_paid"),
                confirm={
                    "title": "אישור סימון חיוב כשולם",
                    "message": "האם לסמן את החיוב כשולם?",
                    "confirm_label": "אישור",
                    "cancel_label": "ביטול",
                },
            )
        )
        actions.append(_cancel_charge_action(charge.id))

    return actions


__all__ = ["get_charge_actions"]
