from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.clients.enums import ClientStatus
from app.common.enums import EntityType, IdNumberType, VatType
from app.core.api_types import ApiDateTime, ApiDecimal
from app.businesses.schemas.business_schemas import BusinessResponse
from app.clients.schemas.impact import ClientCreationImpactResponse


class ClientRecordResponse(BaseModel):
    id: int                                          # ClientRecord.id
    full_name: str                                   # LegalEntity.official_name / owner Person.full_name
    official_name: Optional[str] = None              # compatibility alias for LegalEntity.official_name
    id_number: str                                   # LegalEntity.id_number
    id_number_type: Optional[IdNumberType] = None   # LegalEntity.id_number_type
    entity_type: Optional[EntityType] = None        # LegalEntity.entity_type
    status: ClientStatus = ClientStatus.ACTIVE      # ClientRecord.status
    office_client_number: Optional[int] = None      # ClientRecord.office_client_number
    accountant_name: Optional[str] = None           # ClientRecord.accountant_name
    notes: Optional[str] = None                     # ClientRecord.notes
    # ── Tax reporting (LegalEntity) ───────────────────────────────────────────
    vat_reporting_frequency: Optional[VatType] = None
    vat_exempt_ceiling: Optional[ApiDecimal] = None
    advance_rate: Optional[ApiDecimal] = None
    advance_rate_updated_at: Optional[date] = None
    # ── Contact (Person via PersonLegalEntityLink OWNER) ──────────────────────
    phone: Optional[str] = None
    email: Optional[str] = None
    address_street: Optional[str] = None
    address_building_number: Optional[str] = None
    address_apartment: Optional[str] = None
    address_city: Optional[str] = None
    address_zip_code: Optional[str] = None
    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at: Optional[ApiDateTime] = None        # ClientRecord.created_at
    updated_at: Optional[ApiDateTime] = None        # ClientRecord.updated_at
    created_by: Optional[int] = None               # ClientRecord.created_by
    # ── Enriched (set by API layer) ───────────────────────────────────────────
    active_binder_number: Optional[str] = None

    model_config = {"from_attributes": True}


class ClientRecordListStats(BaseModel):
    active: int = 0
    frozen: int = 0
    closed: int = 0


class ClientRecordListResponse(BaseModel):
    items: list[ClientRecordResponse]
    page: int
    page_size: int
    total: int
    stats: ClientRecordListStats


class CreateClientRecordResponse(BaseModel):
    client_record_id: int
    client: ClientRecordResponse
    business: BusinessResponse
    impact: ClientCreationImpactResponse
