from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.clients.enums import ClientStatus
from app.clients.repositories.client_record_repository import (
    ClientRecordRepository,
    get_full_record,
    get_full_record_including_deleted,
    get_full_records_bulk,
)
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.clients.repositories.person_repository import PersonRepository
from app.common.enums import AdvancePaymentFrequency, EntityType, IdNumberType, VatType


@dataclass
class ClientRecordView:
    id: int
    client_record_id: int
    full_name: str
    id_number: str
    id_number_type: Optional[IdNumberType]
    entity_type: Optional[EntityType]
    status: ClientStatus
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
    advance_payment_frequency: Optional[AdvancePaymentFrequency] = None
    vat_exempt_ceiling: Optional[object] = None
    advance_rate: Optional[object] = None
    advance_rate_updated_at: Optional[object] = None
    annual_revenue: Optional[object] = None
    accountant_id: Optional[int] = None
    created_at: Optional[object] = None
    updated_at: Optional[object] = None
    created_by: Optional[int] = None
    deleted_at: Optional[object] = None
    deleted_by: Optional[int] = None
    restored_at: Optional[object] = None
    restored_by: Optional[int] = None


def _to_view(data: dict | None) -> Optional[ClientRecordView]:
    if not data:
        return None
    return ClientRecordView(client_record_id=data["id"], **data)


class ClientRepository:
    """Compatibility facade over ClientRecordRepository."""

    def __init__(self, db):
        self.db = db
        self.records = ClientRecordRepository(db)

    def create(
        self,
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
        vat_reporting_frequency: Optional[VatType] = None,
        advance_payment_frequency: Optional[AdvancePaymentFrequency] = None,
        vat_exempt_ceiling=None,
        advance_rate=None,
        advance_rate_updated_at=None,
        accountant_id: Optional[int] = None,
        office_client_number: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> ClientRecordView:
        legal_entities = LegalEntityRepository(self.db)
        legal_entity = legal_entities.get_by_id_number(id_number_type, id_number)
        if legal_entity is None:
            legal_entity = legal_entities.create(
                id_number=id_number,
                id_number_type=id_number_type,
                official_name=full_name,
                entity_type=entity_type,
                vat_reporting_frequency=vat_reporting_frequency,
                advance_payment_frequency=advance_payment_frequency,
                vat_exempt_ceiling=vat_exempt_ceiling,
                advance_rate=advance_rate,
            )
        else:
            legal_entity.official_name = full_name
            legal_entity.entity_type = entity_type
            legal_entity.vat_reporting_frequency = vat_reporting_frequency
            legal_entity.advance_payment_frequency = advance_payment_frequency
            legal_entity.vat_exempt_ceiling = vat_exempt_ceiling
            legal_entity.advance_rate = advance_rate
        if advance_rate_updated_at is not None:
            legal_entity.advance_rate_updated_at = advance_rate_updated_at
        PersonRepository(self.db).ensure_owner(
            legal_entity_id=legal_entity.id,
            full_name=full_name,
            id_number=id_number,
            id_number_type=id_number_type,
            phone=phone,
            email=email,
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
        )
        record = self.records.create(
            legal_entity_id=legal_entity.id,
            office_client_number=office_client_number
            or self.records.get_next_office_client_number(),
            accountant_id=accountant_id,
            created_by=created_by,
        )
        return self.get_by_id(record.id)

    def get_by_id(self, entity_id: int) -> Optional[ClientRecordView]:
        return _to_view(get_full_record(self.db, entity_id))

    def get_by_id_including_deleted(self, client_id: int) -> Optional[ClientRecordView]:
        return _to_view(get_full_record_including_deleted(self.db, client_id))

    def get_active_by_id_number(self, id_number: str) -> list[ClientRecordView]:
        return [
            view
            for record in self.records.get_active_by_id_number(id_number)
            if (view := self.get_by_id(record.id)) is not None
        ]

    def get_deleted_by_id_number(self, id_number: str) -> list[ClientRecordView]:
        return [
            view
            for record in self.records.get_deleted_by_id_number(id_number)
            if (view := self.get_by_id_including_deleted(record.id)) is not None
        ]

    def restore(self, client_id: int, restored_by: int) -> Optional[ClientRecordView]:
        record = self.records.restore(client_id, restored_by)
        return self.get_by_id_including_deleted(record.id) if record else None

    def soft_delete(self, client_id: int, deleted_by: int) -> bool:
        return self.records.soft_delete(client_id, deleted_by)

    def list(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        sort_by: str = "full_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> list[ClientRecordView]:
        records = self.records.list(
            search=search,
            status=status,
            sort_by="official_name" if sort_by == "full_name" else sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return self._views_for_records(records)

    def count(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
    ) -> int:
        return self.records.count(search=search, status=status)

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ClientRecordView], int]:
        records, total = self.records.search(
            query=query,
            client_name=client_name,
            id_number=id_number,
            page=page,
            page_size=page_size,
        )
        return self._views_for_records(records), total

    def list_by_ids(self, client_ids: list[int]) -> list[ClientRecordView]:
        return self._views_for_records(self.records.list_by_ids(client_ids))

    def list_all(self) -> list[ClientRecordView]:
        return self._views_for_records(self.records.list_all())

    def update(self, client_id: int, **fields) -> Optional[ClientRecordView]:
        record = self.records.get_by_id(client_id)
        if not record:
            return None
        legal_entity = LegalEntityRepository(self.db).get_by_id(record.legal_entity_id)
        if not legal_entity:
            return None
        person = PersonRepository(self.db).get_owner_for_legal_entity(legal_entity.id)
        person_fields = {
            "phone",
            "email",
            "address_street",
            "address_building_number",
            "address_apartment",
            "address_city",
            "address_zip_code",
        }
        legal_entity_fields = {
            "entity_type",
            "vat_reporting_frequency",
            "advance_payment_frequency",
            "advance_rate",
            "advance_rate_updated_at",
            "annual_revenue",
        }
        record_fields = {"status", "accountant_id"}
        if "full_name" in fields:
            legal_entity.official_name = fields["full_name"]
            if person is not None:
                person.full_name = fields["full_name"]
        for key, value in fields.items():
            if key in person_fields and person is not None:
                setattr(person, key, value)
            elif key in legal_entity_fields:
                setattr(legal_entity, key, value)
            elif key in record_fields:
                setattr(record, key, value)
        self.db.flush()
        return self.get_by_id(client_id)

    def count_by_status(self) -> dict[ClientStatus, int]:
        return self.records.count_by_status()

    def get_next_office_client_number(self) -> int:
        return self.records.get_next_office_client_number()

    def _views_for_records(self, records) -> list[ClientRecordView]:
        full_map = get_full_records_bulk(self.db, [record.id for record in records])
        return [
            view
            for record in records
            if (view := _to_view(full_map.get(record.id))) is not None
        ]
