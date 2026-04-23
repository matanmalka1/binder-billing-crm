from __future__ import annotations

from typing import Any, Literal, NotRequired, Optional, TypedDict


def _value(raw: Any) -> str:
    return raw.value if hasattr(raw, "value") else str(raw)


def _generate_action_id(resource: str, resource_id: int, key: str) -> str:
    return f"{resource}-{resource_id}-{key}"


HttpMethod = Literal["get", "post", "put", "patch", "delete"]


class ConfirmInput(TypedDict):
    name: str
    label: str
    type: Literal["text"]
    required: bool


class ActionConfirm(TypedDict):
    title: str
    message: str
    confirm_label: str
    cancel_label: str
    inputs: NotRequired[list[ConfirmInput]]


class ActionContract(TypedDict):
    id: str
    key: str
    label: str
    method: HttpMethod
    endpoint: str
    payload: NotRequired[dict[str, Any]]
    confirm: NotRequired[ActionConfirm]


_VALID_METHODS = {"get", "post", "put", "patch", "delete"}


def build_confirm(
    title: str,
    message: str,
    *,
    confirm_label: str = "אישור",
    cancel_label: str = "ביטול",
    inputs: Optional[list[ConfirmInput]] = None,
) -> ActionConfirm:
    confirm: ActionConfirm = {
        "title": title,
        "message": message,
        "confirm_label": confirm_label,
        "cancel_label": cancel_label,
    }
    if inputs is not None:
        confirm["inputs"] = inputs
    return confirm


def _validate_confirm(confirm: ActionConfirm) -> None:
    if "inputs" not in confirm:
        return
    for item in confirm["inputs"]:
        if item["type"] != "text":
            raise ValueError("Action confirm input type is not supported")


def build_action(
    key: str,
    label: str,
    method: HttpMethod,
    endpoint: str,
    action_id: str,
    payload: Optional[dict[str, Any]] = None,
    confirm: Optional[ActionConfirm] = None,
) -> ActionContract:
    if method not in _VALID_METHODS:
        raise ValueError("Action method is not supported")
    action: ActionContract = {
        "id": action_id,
        "key": key,
        "label": label,
        "method": method,
        "endpoint": endpoint,
    }

    if payload is not None:
        action["payload"] = payload

    if confirm is not None:
        _validate_confirm(confirm)
        action["confirm"] = confirm

    return action


__all__ = [
    "_value",
    "_generate_action_id",
    "ActionConfirm",
    "ActionContract",
    "ConfirmInput",
    "HttpMethod",
    "build_action",
    "build_confirm",
]
