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
            )
        )

    if status in (BinderStatus.READY_FOR_PICKUP.value, BinderStatus.OVERDUE.value):
        actions.append(
            build_action(
                key="return",
                label="החזרת תיק",
                method="post",
                endpoint=f"/binders/{binder.id}/return",
                confirm_required=True,
                confirm_title="אישור החזרת תיק",
                confirm_message="האם לאשר החזרת תיק ללקוח?",
                confirm_label="אישור",
                cancel_label="ביטול",
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
                confirm_required=True,
                confirm_title="אישור הקפאת לקוח",
                confirm_message="האם להקפיא את הלקוח?",
                confirm_label="הקפאה",
                cancel_label="ביטול",
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
            )
        )
        actions.append(
            build_action(
                key="cancel_charge",
                label="ביטול חיוב",
                method="post",
                endpoint=f"/charges/{charge.id}/cancel",
                confirm_required=True,
                confirm_title="אישור ביטול חיוב",
                confirm_message="האם לבטל את החיוב?",
                confirm_label="ביטול",
                cancel_label="חזרה",
            )
        )

    if status == ChargeStatus.ISSUED.value:
        actions.append(
            build_action(
                key="mark_paid",
                label="סימון חיוב כשולם",
                method="post",
                endpoint=f"/charges/{charge.id}/mark-paid",
            )
        )
        actions.append(
            build_action(
                key="cancel_charge",
                label="ביטול חיוב",
                method="post",
                endpoint=f"/charges/{charge.id}/cancel",
                confirm_required=True,
                confirm_title="אישור ביטול חיוב",
                confirm_message="האם לבטל את החיוב?",
                confirm_label="ביטול",
                cancel_label="חזרה",
            )
        )

    return actions


def build_action(
    key: str,
    label: str,
    method: str,
    endpoint: str,
    payload: Optional[dict[str, Any]] = None,
    confirm_required: bool = False,
    confirm_title: Optional[str] = None,
    confirm_message: Optional[str] = None,
    confirm_label: Optional[str] = None,
    cancel_label: Optional[str] = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "key": key,
        "label": label,
        "method": method,
        "endpoint": endpoint,
        "confirm_required": confirm_required,
    }

    if payload is not None:
        action["payload"] = payload
    if confirm_title:
        action["confirm_title"] = confirm_title
    if confirm_message:
        action["confirm_message"] = confirm_message
    if confirm_label:
        action["confirm_label"] = confirm_label
    if cancel_label:
        action["cancel_label"] = cancel_label

    return action
