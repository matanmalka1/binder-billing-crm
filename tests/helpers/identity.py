from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.businesses.models.business import Business, BusinessStatus
from app.clients.enums import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.common.enums import EntityType, IdNumberType, VatType


@dataclass
class SeededClient:
    id: int
    legal_entity_id: int
    full_name: str
    id_number: str
    id_number_type: IdNumberType
    entity_type: Optional[EntityType]
    phone: Optional[str]
    email: Optional[str]
    address_street: Optional[str]
    address_building_number: Optional[str]
    address_apartment: Optional[str]
    address_city: Optional[str]
    address_zip_code: Optional[str]
    office_client_number: Optional[int]
    notes: Optional[str]
    vat_reporting_frequency: Optional[VatType]
    vat_exempt_ceiling: Optional[object]
    advance_rate: Optional[object]
    advance_rate_updated_at: Optional[date]
    accountant_id: Optional[int]
    status: ClientStatus
    created_by: Optional[int]
    deleted_at: Optional[object]


def seed_client_identity(
    db: Session,
    *,
    full_name: str,
    id_number: str,
    id_number_type: IdNumberType = IdNumberType.INDIVIDUAL,
    entity_type: Optional[EntityType] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    address_street: Optional[str] = None,
    address_building_number: Optional[str] = None,
    address_apartment: Optional[str] = None,
    address_city: Optional[str] = None,
    address_zip_code: Optional[str] = None,
    office_client_number: Optional[int] = None,
    notes: Optional[str] = None,
    vat_reporting_frequency: Optional[VatType] = None,
    vat_exempt_ceiling=None,
    advance_rate=None,
    advance_rate_updated_at: Optional[date] = None,
    accountant_id: Optional[int] = None,
    status: ClientStatus = ClientStatus.ACTIVE,
    created_by: Optional[int] = None,
    deleted_at=None,
    create_person: bool = True,
    client_record_id: Optional[int] = None,
) -> SeededClient:
    legal_entity = LegalEntity(
        id_number=id_number,
        id_number_type=id_number_type,
        entity_type=entity_type,
        official_name=full_name,
        vat_reporting_frequency=vat_reporting_frequency,
        vat_exempt_ceiling=vat_exempt_ceiling,
        advance_rate=advance_rate,
        advance_rate_updated_at=advance_rate_updated_at,
    )
    db.add(legal_entity)
    db.flush()

    if create_person:
        person_type = IdNumberType.OTHER if id_number_type == IdNumberType.CORPORATION else id_number_type
        person = Person(
            full_name=full_name,
            id_number=id_number,
            id_number_type=person_type,
            phone=phone,
            email=email,
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
        )
        db.add(person)
        db.flush()
        db.add(
            PersonLegalEntityLink(
                person_id=person.id,
                legal_entity_id=legal_entity.id,
                role=PersonLegalEntityRole.OWNER,
            )
        )
        db.flush()

    record = ClientRecord(
        id=client_record_id,
        legal_entity_id=legal_entity.id,
        office_client_number=office_client_number,
        accountant_id=accountant_id,
        status=status,
        notes=notes,
        created_by=created_by,
        deleted_at=deleted_at,
    )
    db.add(record)
    db.flush()

    return SeededClient(
        id=record.id,
        legal_entity_id=legal_entity.id,
        full_name=full_name,
        id_number=id_number,
        id_number_type=id_number_type,
        entity_type=entity_type,
        phone=phone,
        email=email,
        address_street=address_street,
        address_building_number=address_building_number,
        address_apartment=address_apartment,
        address_city=address_city,
        address_zip_code=address_zip_code,
        office_client_number=office_client_number,
        notes=notes,
        vat_reporting_frequency=vat_reporting_frequency,
        vat_exempt_ceiling=vat_exempt_ceiling,
        advance_rate=advance_rate,
        advance_rate_updated_at=advance_rate_updated_at,
        accountant_id=accountant_id,
        status=status,
        created_by=created_by,
        deleted_at=deleted_at,
    )


def seed_business(
    db: Session,
    *,
    legal_entity_id: int,
    business_name: str,
    opened_at: Optional[date] = None,
    status: BusinessStatus = BusinessStatus.ACTIVE,
    created_by: Optional[int] = None,
    notes: Optional[str] = None,
) -> Business:
    business = Business(
        legal_entity_id=legal_entity_id,
        business_name=business_name,
        opened_at=opened_at or date.today(),
        status=status,
        created_by=created_by,
        notes=notes,
    )
    db.add(business)
    db.flush()
    return business


def seed_client_with_business(
    db: Session,
    *,
    full_name: str,
    id_number: str,
    business_name: Optional[str] = None,
    id_number_type: IdNumberType = IdNumberType.INDIVIDUAL,
    opened_at: Optional[date] = None,
    **client_fields,
) -> tuple[SeededClient, Business]:
    client = seed_client_identity(
        db,
        full_name=full_name,
        id_number=id_number,
        id_number_type=id_number_type,
        **client_fields,
    )
    business = seed_business(
        db,
        legal_entity_id=client.legal_entity_id,
        business_name=business_name or full_name,
        opened_at=opened_at,
    )
    business.client_id = client.id
    business.client_record_id = client.id
    db.flush()
    return client, business
