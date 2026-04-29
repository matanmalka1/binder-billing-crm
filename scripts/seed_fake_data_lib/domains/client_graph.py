from __future__ import annotations

from dataclasses import dataclass

from app.common.enums import EntityType, VatType


@dataclass(slots=True)
class SeedClient:
    id: int
    legal_entity_id: int
    office_client_number: int | None
    full_name: str
    email: str | None
    phone: str | None
    city: str | None
    entity_type: EntityType | None
    vat_reporting_frequency: VatType | None
