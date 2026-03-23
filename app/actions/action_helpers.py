from __future__ import annotations

from typing import Any, Optional


def _value(raw: Any) -> str:
    return raw.value if hasattr(raw, "value") else str(raw)


def _generate_action_id(resource: str, resource_id: int, key: str) -> str:
    return f"{resource}-{resource_id}-{key}"


def build_action(
    key: str,
    label: str,
    method: str,
    endpoint: str,
    action_id: str,
    payload: Optional[dict[str, Any]] = None,
    confirm: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "id": action_id,
        "key": key,
        "label": label,
        "method": method,
        "endpoint": endpoint,
    }

    if payload is not None:
        action["payload"] = payload

    if confirm is not None:
        action["confirm"] = confirm

    return action


__all__ = ["_value", "_generate_action_id", "build_action"]
