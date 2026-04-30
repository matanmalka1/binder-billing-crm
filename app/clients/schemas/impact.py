from typing import Optional

from pydantic import BaseModel

from app.core.api_types import ApiDecimal


class CreationImpactItem(BaseModel):
    label: str
    count: int


class ClientCreationImpactResponse(BaseModel):
    items: list[CreationImpactItem]
    years_scope: int
    note: Optional[str] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = None
