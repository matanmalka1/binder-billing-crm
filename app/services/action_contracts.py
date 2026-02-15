from __future__ import annotations

from typing import Any, Optional

from app.models import (
    Binder,
    BinderStatus,
    Charge,
    ChargeStatus,
    Client,
    ClientStatus,
    UserRole,
)


def _value(raw: Any) -> str:
    return raw.value if hasattr(raw, "value") else str(raw)


def _generate_action_id(resource: str, resource_id: int, key: str) -> str:
    return f"{resource}-{resource_id}-{key}"


def get_binder_actions(binder: Binder) -> list[dict[str, Any]]:
    """Return executable actions for a binder (with endpoints & metadata)."""

    status = _value(binder.status)
    actions: list[dict[str, Any]] = []

    if status in (BinderStatus.IN_OFFICE.value, BinderStatus.OVERDUE.value):
        actions.append(
            build_action(
                key="ready",
                label="מוכן לאיסוף",
                method="post",
                endpoint=f"/binders/{binder.id}/ready",
                action_id=_generate_action_id("binder", binder.id, "ready"),
            )
        )

    if status in (BinderStatus.READY_FOR_PICKUP.value, BinderStatus.OVERDUE.value):
        actions.append(
            build_action(
                key="return",
                label="החזרת תיק",
                method="post",
                endpoint=f"/binders/{binder.id}/return",
                action_id=_generate_action_id("binder", binder.id, "return"),
                confirm={
                    "title": "אישור החזרת תיק",
                    "message": "האם לאשר החזרת תיק ללקוח?",
                    "confirm_label": "אישור",
                    "cancel_label": "ביטול",
                },
            )
        )

    return actions


def get_client_actions(client: Client, user_role: Optional[UserRole] = None) -> list[dict[str, Any]]:
    """Return executable actions for a client (role-aware)."""

    status = _value(client.status)
    actions: list[dict[str, Any]] = []

    if status == ClientStatus.ACTIVE.value and (user_role == UserRole.ADVISOR or user_role is None):
        actions.append(
            build_action(
                key="freeze",
                label="הקפאת לקוח",
                method="patch",
                endpoint=f"/clients/{client.id}",
                payload={"status": "frozen"},
                action_id=_generate_action_id("client", client.id, "freeze"),
                confirm={
                    "title": "אישור הקפאת לקוח",
                    "message": "האם להקפיא את הלקוח?",
                    "confirm_label": "הקפאה",
                    "cancel_label": "ביטול",
                },
            )
        )

    if status == ClientStatus.FROZEN.value:
        actions.append(
            build_action(
                key="activate",
                label="הפעלת לקוח",
                method="patch",
                endpoint=f"/clients/{client.id}",
                payload={"status": "active"},
                action_id=_generate_action_id("client", client.id, "activate"),
            )
        )

    return actions


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
        actions.append(
            build_action(
                key="cancel_charge",
                label="ביטול חיוב",
                method="post",
                endpoint=f"/charges/{charge.id}/cancel",
                action_id=_generate_action_id("charge", charge.id, "cancel_charge"),
                confirm={
                    "title": "אישור ביטול חיוב",
                    "message": "האם לבטל את החיוב?",
                    "confirm_label": "ביטול",
                    "cancel_label": "חזרה",
                },
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
            )
        )
        actions.append(
            build_action(
                key="cancel_charge",
                label="ביטול חיוב",
                method="post",
                endpoint=f"/charges/{charge.id}/cancel",
                action_id=_generate_action_id("charge", charge.id, "cancel_charge"),
                confirm={
                    "title": "אישור ביטול חיוב",
                    "message": "האם לבטל את החיוב?",
                    "confirm_label": "ביטול",
                    "cancel_label": "חזרה",
                },
            )
        )

    return actions


def build_action(
    key: str,
    label: str,
    method: str,
    endpoint: str,
    action_id: str,
    payload: Optional[dict[str, Any]] = None,
    confirm: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "id": action_id,
        "key": key,
        "label": label,
        "method": method,
        "endpoint": endpoint,
        "confirm": confirm,
    }

    if payload is not None:
        action["payload"] = payload

    return action
