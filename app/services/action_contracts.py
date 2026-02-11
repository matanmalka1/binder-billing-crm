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


def get_binder_actions(binder: Binder) -> list[str]:
    status = _value(binder.status)

    if status == BinderStatus.IN_OFFICE.value:
        return ["ready"]
    if status == BinderStatus.READY_FOR_PICKUP.value:
        return ["return"]
    if status == BinderStatus.OVERDUE.value:
        return ["ready", "return"]

    return []


def get_client_actions(client: Client, user_role: Optional[UserRole] = None) -> list[str]:
    status = _value(client.status)

    if status == ClientStatus.ACTIVE.value:
        if user_role == UserRole.ADVISOR or user_role is None:
            return ["freeze"]
        return []

    if status == ClientStatus.FROZEN.value:
        return ["activate"]

    return []


def get_charge_actions(charge: Charge) -> list[str]:
    status = _value(charge.status)

    if status == ChargeStatus.DRAFT.value:
        return ["issue_charge", "cancel_charge"]
    if status == ChargeStatus.ISSUED.value:
        return ["mark_paid", "cancel_charge"]

    return []


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
