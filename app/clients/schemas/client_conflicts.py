from pydantic import BaseModel

from app.core.api_types import ApiDateTime


class ActiveClientSummary(BaseModel):
    id: int
    full_name: str
    id_number: str

    model_config = {"from_attributes": True}


class DeletedClientSummary(BaseModel):
    id: int
    full_name: str
    id_number: str
    deleted_at: ApiDateTime

    model_config = {"from_attributes": True}


class ClientConflictInfo(BaseModel):
    id_number: str
    active_clients: list[ActiveClientSummary]
    deleted_clients: list[DeletedClientSummary]
