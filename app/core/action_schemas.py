from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ActionDescriptor(BaseModel):
    key: str
    label: str
    type: Literal["link", "mutation", "modal"]
    route: str | None = None
    endpoint: str | None = None
    method: Literal["get", "post", "patch", "put", "delete"] | None = None
    task_id: int | None = None
    payload_schema: Literal["none", "simple", "requires_input"] = "none"
    confirm: bool = False
    confirm_title: str | None = None
    confirm_message: str | None = None
    variant: Literal["primary", "secondary", "danger"] = "secondary"
    disabled: bool = False
    disabled_reason: str | None = None


__all__ = ["ActionDescriptor"]
