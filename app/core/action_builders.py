from __future__ import annotations

from typing import Literal, Optional

from app.core.action_schemas import ActionDescriptor

ActionVariant = Literal["primary", "secondary", "danger"]


def link_action(
    key: str,
    label: str,
    route: str,
    *,
    primary: bool = False,
) -> ActionDescriptor:
    return ActionDescriptor(
        key=key,
        label=label,
        type="link",
        route=route,
        variant="primary" if primary else "secondary",
    )


def mutation_action(
    key: str,
    label: str,
    endpoint: str,
    *,
    method: Literal["get", "post", "patch", "put", "delete"] = "post",
    task_id: Optional[int] = None,
    confirm_title: Optional[str] = None,
    confirm_message: Optional[str] = None,
    variant: ActionVariant = "secondary",
    payload_schema: Literal["none", "simple", "requires_input"] = "none",
) -> ActionDescriptor:
    return ActionDescriptor(
        key=key,
        label=label,
        type="mutation",
        endpoint=endpoint,
        method=method,
        task_id=task_id,
        confirm=confirm_title is not None or confirm_message is not None,
        confirm_title=confirm_title,
        confirm_message=confirm_message,
        variant=variant,
        payload_schema=payload_schema,
    )


def modal_action(
    key: str,
    label: str,
    *,
    task_id: Optional[int] = None,
    primary: bool = False,
    variant: Optional[ActionVariant] = None,
) -> ActionDescriptor:
    return ActionDescriptor(
        key=key,
        label=label,
        type="modal",
        task_id=task_id,
        variant=variant or ("primary" if primary else "secondary"),
    )


__all__ = ["link_action", "mutation_action", "modal_action"]
