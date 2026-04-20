from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.clients.enums import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.clients.repositories.person_repository import PersonRepository
from app.common.enums import EntityType, IdNumberType, VatType
from app.common.repositories.base_repository import BaseRepository


@dataclass
class LegacyClientView:
    id: int
    client_record_id: int
    full_name: str
    id_number: str
    id_number_type: Optional[IdNumberType]
    entity_type: Optional[EntityType]
    status: ClientStatus
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
    advance_rate_updated_at: Optional[object]
    accountant_name: Optional[str]
    created_at: Optional[object]
    updated_at: Optional[object]
    deleted_at: Optional[object]
    deleted_by: Optional[int]
    restored_at: Optional[object]
    restored_by: Optional[int]


class ClientRepository(BaseRepository):
    """Legacy-shaped client reads/writes backed by ClientRecord + LegalEntity + Person."""

    _SORTABLE_FIELDS = {
        "full_name": LegalEntity.official_name,
        "official_name": LegalEntity.official_name,
        "created_at": ClientRecord.created_at,
        "status": ClientRecord.status,
    }

    def _base_query(self, *, include_deleted: bool = False):
        query = (
            self.db.query(ClientRecord, LegalEntity, Person)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .outerjoin(
                PersonLegalEntityLink,
                (
                    (PersonLegalEntityLink.legal_entity_id == LegalEntity.id)
                    & (PersonLegalEntityLink.role == PersonLegalEntityRole.OWNER)
                ),
            )
            .outerjoin(Person, Person.id == PersonLegalEntityLink.person_id)
        )
        if not include_deleted:
            query = query.filter(ClientRecord.deleted_at.is_(None))
        return query

    def _to_legacy_view(
        self,
        record: ClientRecord,
        legal_entity: LegalEntity,
        person: Optional[Person],
    ) -> LegacyClientView:
        full_name = person.full_name if person and person.full_name else legal_entity.official_name
        return LegacyClientView(
            id=record.id,
            client_record_id=record.id,
            full_name=full_name,
            id_number=legal_entity.id_number,
            id_number_type=legal_entity.id_number_type,
            entity_type=legal_entity.entity_type,
            status=record.status,
            phone=person.phone if person else None,
            email=person.email if person else None,
            address_street=person.address_street if person else None,
            address_building_number=person.address_building_number if person else None,
            address_apartment=person.address_apartment if person else None,
            address_city=person.address_city if person else None,
            address_zip_code=person.address_zip_code if person else None,
            office_client_number=record.office_client_number,
            notes=record.notes,
            vat_reporting_frequency=legal_entity.vat_reporting_frequency,
            vat_exempt_ceiling=legal_entity.vat_exempt_ceiling,
            advance_rate=legal_entity.advance_rate,
            advance_rate_updated_at=legal_entity.advance_rate_updated_at,
            accountant_name=record.accountant_name,
            created_at=record.created_at,
            updated_at=record.updated_at,
            deleted_at=record.deleted_at,
            deleted_by=record.deleted_by,
            restored_at=record.restored_at,
            restored_by=record.restored_by,
        )

    def _first_view(self, query) -> Optional[LegacyClientView]:
        row = query.first()
        return self._to_legacy_view(*row) if row else None

    def _list_views(self, query) -> list[LegacyClientView]:
        return [self._to_legacy_view(*row) for row in query.all()]

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
        vat_exempt_ceiling=None,
        advance_rate=None,
        advance_rate_updated_at=None,
        accountant_name: Optional[str] = None,
        office_client_number: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> LegacyClientView:
        legal_entity_repo = LegalEntityRepository(self.db)
        legal_entity = legal_entity_repo.get_by_id_number(id_number_type, id_number)
        if not legal_entity:
            legal_entity = legal_entity_repo.create(
                id_number=id_number,
                id_number_type=id_number_type,
                official_name=full_name,
                entity_type=entity_type,
                vat_reporting_frequency=vat_reporting_frequency,
                vat_exempt_ceiling=vat_exempt_ceiling,
                advance_rate=advance_rate,
            )
        else:
            legal_entity.official_name = full_name
            legal_entity.entity_type = entity_type
            legal_entity.vat_reporting_frequency = vat_reporting_frequency
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
        record = ClientRecordRepository(self.db).create(
            legal_entity_id=legal_entity.id,
            office_client_number=office_client_number or self.get_next_office_client_number(),
            accountant_name=accountant_name,
            created_by=created_by,
        )
        return self.get_by_id(record.id)

    def get_by_id(self, client_id: int) -> Optional[LegacyClientView]:
        return self._first_view(
            self._base_query().filter(ClientRecord.id == client_id)
        )

    def get_by_id_including_deleted(self, client_id: int) -> Optional[LegacyClientView]:
        return self._first_view(
            self._base_query(include_deleted=True).filter(ClientRecord.id == client_id)
        )

    def get_active_by_id_number(self, id_number: str) -> list[LegacyClientView]:
        return self._list_views(
            self._base_query()
            .filter(LegalEntity.id_number == id_number)
            .order_by(ClientRecord.id.asc())
        )

    def get_deleted_by_id_number(self, id_number: str) -> list[LegacyClientView]:
        return self._list_views(
            self._base_query(include_deleted=True)
            .filter(
                LegalEntity.id_number == id_number,
                ClientRecord.deleted_at.isnot(None),
            )
            .order_by(ClientRecord.deleted_at.desc())
        )

    def restore(self, client_id: int, restored_by: int) -> Optional[LegacyClientView]:
        record = ClientRecordRepository(self.db).restore(client_id, restored_by)
        return self.get_by_id_including_deleted(record.id) if record else None

    def soft_delete(self, client_id: int, deleted_by: int) -> bool:
        return ClientRecordRepository(self.db).soft_delete(client_id, deleted_by)

    def _apply_list_filters(self, query, search=None, status=None):
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                LegalEntity.official_name.ilike(term) | LegalEntity.id_number.ilike(term)
            )
        if status:
            query = query.filter(ClientRecord.status == status)
        return query

    def list(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        sort_by: str = "full_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> list[LegacyClientView]:
        from sqlalchemy import asc, desc

        query = self._apply_list_filters(self._base_query(), search, status)
        col = self._SORTABLE_FIELDS.get(sort_by, LegalEntity.official_name)
        query = query.order_by(desc(col) if sort_order == "desc" else asc(col))
        query = query.offset((page - 1) * page_size).limit(page_size)
        return self._list_views(query)

    def count(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
    ) -> int:
        return self._apply_list_filters(self._base_query(), search, status).count()

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LegacyClientView], int]:
        q = self._base_query()
        if query:
            term = f"%{query.strip()}%"
            q = q.filter(LegalEntity.official_name.ilike(term) | LegalEntity.id_number.ilike(term))
        if client_name:
            q = q.filter(LegalEntity.official_name.ilike(f"%{client_name.strip()}%"))
        if id_number:
            q = q.filter(LegalEntity.id_number.ilike(f"%{id_number.strip()}%"))
        total = q.count()
        items = q.order_by(LegalEntity.official_name.asc()).offset((page - 1) * page_size).limit(page_size)
        return self._list_views(items), total

    def list_by_ids(self, client_ids: list[int]) -> list[LegacyClientView]:
        if not client_ids:
            return []
        return self._list_views(
            self._base_query().filter(ClientRecord.id.in_(client_ids))
        )

    def list_all(self) -> list[LegacyClientView]:
        return self._list_views(
            self._base_query().order_by(LegalEntity.official_name.asc())
        )

    def update(self, client_id: int, **fields) -> Optional[LegacyClientView]:
        row = (
            self._base_query()
            .filter(ClientRecord.id == client_id)
            .first()
        )
        if not row:
            return None
        record, legal_entity, person = row
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
            "vat_exempt_ceiling",
            "advance_rate",
            "advance_rate_updated_at",
        }
        record_fields = {"status", "accountant_name", "notes"}
        owner_requested = "full_name" in fields or bool(person_fields.intersection(fields))
        if owner_requested and person is None:
            PersonRepository(self.db).ensure_owner(
                legal_entity_id=legal_entity.id,
                full_name=fields.get("full_name", legal_entity.official_name),
                id_number=legal_entity.id_number,
                id_number_type=legal_entity.id_number_type,
            )
            person = PersonRepository(self.db).get_owner_for_legal_entity(legal_entity.id)

        if "full_name" in fields:
            legal_entity.official_name = fields["full_name"]
            if person:
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
        from sqlalchemy import func

        rows = (
            self.db.query(ClientRecord.status, func.count(ClientRecord.id))
            .filter(ClientRecord.deleted_at.is_(None))
            .group_by(ClientRecord.status)
            .all()
        )
        return {status: count for status, count in rows}

    def get_next_office_client_number(self) -> int:
        return ClientRecordRepository(self.db).get_next_office_client_number()
