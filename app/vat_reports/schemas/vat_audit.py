"""Pydantic schemas for VAT audit trail."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.core.api_types import ApiDateTime


class VatAuditLogResponse(BaseModel):
    id: int
    work_item_id: int
    performed_by: int
    performed_by_name: Optional[str] = None
    action: str
    old_value: Optional[str]
    new_value: Optional[str]
    note: Optional[str]
    performed_at: ApiDateTime

    model_config = {"from_attributes": True}


class VatAuditTrailResponse(BaseModel):
    items: list[VatAuditLogResponse]
