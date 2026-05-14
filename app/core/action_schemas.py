from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class ActionDescriptor(BaseModel):
    key: str
    label: str
    type: Literal["link", "mutation", "modal"]
    route: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[Literal["get", "post", "patch", "put", "delete"]] = None
    task_id: Optional[int] = None
    payload_schema: Literal["none", "simple", "requires_input"] = "none"
    confirm: bool = False
    confirm_title: Optional[str] = None
    confirm_message: Optional[str] = None
    variant: Literal["primary", "secondary", "danger"] = "secondary"
    disabled: bool = False
    disabled_reason: Optional[str] = None


__all__ = ["ActionDescriptor"]
