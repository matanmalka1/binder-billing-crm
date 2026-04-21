from typing import Optional
from pydantic import BaseModel
from app.core.api_types import ApiDateTime, PaginatedResponse


class EntityNoteResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    note: str
    created_by: Optional[int] = None
    created_at: ApiDateTime
    updated_at: Optional[ApiDateTime] = None

    model_config = {"from_attributes": True}


EntityNoteListResponse = PaginatedResponse[EntityNoteResponse]


class EntityNoteCreateRequest(BaseModel):
    note: str


class EntityNoteUpdateRequest(BaseModel):
    note: str
