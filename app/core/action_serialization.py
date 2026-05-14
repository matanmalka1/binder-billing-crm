from __future__ import annotations

from typing import Any

from app.core.action_schemas import ActionDescriptor

_STABLE_FRONTEND_FIELDS = frozenset(
    {
        "key",
        "label",
        "type",
        "method",
        "endpoint",
        "route",
        "confirm",
        "confirm_title",
        "confirm_message",
        "variant",
        "payload_schema",
        "task_id",
    }
)


def dump_action_descriptor(action: ActionDescriptor) -> dict[str, Any]:
    return action.model_dump(include=_STABLE_FRONTEND_FIELDS, exclude_none=True)


__all__ = ["dump_action_descriptor"]
