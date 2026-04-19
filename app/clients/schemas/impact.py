from typing import Optional

from pydantic import BaseModel


class CreationImpactItem(BaseModel):
    label: str
    count: int


class ClientCreationImpactResponse(BaseModel):
    items: list[CreationImpactItem]
    years_scope: int
    note: Optional[str] = None
