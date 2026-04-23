from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.businesses.schemas.business_schemas import BusinessResponse
from app.clients.enums import ClientStatus
from app.clients.schemas.impact import ClientCreationImpactResponse
from app.common.enums import EntityType, IdNumberType, VatType
from app.core.api_types import ApiDateTime, ApiDecimal


class ClientResponse(BaseModel):
    id: int
    full_name: str
    id_number: str
    id_number_type: Optional[IdNumberType] = None
    entity_type: Optional[EntityType] = None
    status: ClientStatus = ClientStatus.ACTIVE
    phone: Optional[str] = None
    email: Optional[str] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    office_client_number: Optional[int] = None
    notes: Optional[str] = None
    vat_reporting_frequency: Optional[VatType] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = None
    advance_rate: Optional[ApiDecimal] = None
    advance_rate_updated_at: Optional[date] = None
    accountant_name: Optional[str] = None
    created_at: Optional[ApiDateTime] = None
    updated_at: Optional[ApiDateTime] = None
    active_binder_number: Optional[str] = None

    model_config = {"from_attributes": True}


class ClientListStats(BaseModel):
    active: int = 0
    frozen: int = 0
    closed: int = 0


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    page: int
    page_size: int
    total: int
    stats: ClientListStats


class CreateClientResponse(BaseModel):
    client_record_id: int
    client: ClientResponse
    business: BusinessResponse
    impact: ClientCreationImpactResponse


class ClientImportError(BaseModel):
    row: int
    error: str


class ClientImportResponse(BaseModel):
    created: int
    total_rows: int
    errors: list[ClientImportError]
