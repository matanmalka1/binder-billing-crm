"""Pydantic schemas for the generic entity audit trail."""

from typing import Optional

from pydantic import BaseModel

from app.core.api_types import ApiDateTime


class EntityAuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    performed_by: int
    performed_by_name: Optional[str] = None
    action: str
    old_value: Optional[str]
    new_value: Optional[str]
    note: Optional[str]
    performed_at: ApiDateTime

    model_config = {"from_attributes": True}


class EntityAuditTrailResponse(BaseModel):
    items: list[EntityAuditLogResponse]
