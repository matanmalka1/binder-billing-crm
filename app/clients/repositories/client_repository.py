from __future__ import annotations

# Re-export so callers can access new ClientRecord+LegalEntity query methods
# without changing their import path. The Client-based methods below remain
# until step 5.8 removes the Client model entirely.
from app.clients.repositories.client_record_repository import ClientRecordRepository  # noqa: F401

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import asc, desc, func

from app.common.repositories.base_repository import BaseRepository
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.clients.enums import ClientStatus
from app.clients.models.client import IdNumberType
from app.common.enums import EntityType, VatType
from app.utils.time_utils import utcnow


@dataclass
class LegacyClientView:
    id: int
    client_record_id: int
    full_name: str
    id_number: str
    id_number_type: Optional[IdNumberType] # type: ignore
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
    """Data access layer for Client entities — identity only, no business logic."""

    def _legacy_client_active_query(self):
        return self.db.query(Client).filter(Client.deleted_at.is_(None))

    def _legacy_client_deleted_query(self):
        return self.db.query(Client).filter(Client.deleted_at.isnot(None))

    def create(
        self,
        full_name: str,
        id_number: str,
        id_number_type: IdNumberType = IdNumberType.INDIVIDUAL, # type: ignore
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
    ) -> Client:
        """Create a new client (identity + tax profile)."""
        client = Client(
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
            vat_reporting_frequency=vat_reporting_frequency,
            vat_exempt_ceiling=vat_exempt_ceiling,
            advance_rate=advance_rate,
            advance_rate_updated_at=advance_rate_updated_at,
            accountant_name=accountant_name,
            office_client_number=office_client_number,
            created_by=created_by,
        )
        self.db.add(client)
        self.db.flush()
        return client

    def get_by_id(self, client_id: int) -> Optional[Client]:
        """Retrieve client by ID (excludes soft-deleted)."""
        return (
            self.db.query(Client)
            .filter(Client.id == client_id, Client.deleted_at.is_(None))
            .first()
        )

    def get_by_id_including_deleted(self, client_id: int) -> Optional[Client]:
        """Retrieve client by ID regardless of deletion status."""
        return (
            self.db.query(Client)
            .filter(Client.id == client_id)
            .first()
        )

    def _legacy_query(self):
        return (
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

    def _to_legacy_view(
        self, record: ClientRecord, legal_entity: LegalEntity, person: Optional[Person]
    ) -> LegacyClientView:
        return LegacyClientView(
            id=record.id,
            client_record_id=record.id,
            full_name=person.full_name if person and person.full_name else legal_entity.official_name,
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

    def _legacy_list(self, query) -> list[LegacyClientView]:
        return [self._to_legacy_view(record, legal_entity, person) for record, legal_entity, person in query.all()]

    def get_active_by_id_number(self, id_number: str) -> list[LegacyClientView]:
        """Retrieve active ClientRecords by ID number in legacy Client shape."""
        legacy_any = self.db.query(Client.id).filter(Client.id_number == id_number).first()
        if legacy_any:
            return (
                self._legacy_client_active_query()
                .filter(Client.id_number == id_number)
                .all()
            )
        query = (
            self._legacy_query()
            .filter(
                LegalEntity.id_number == id_number,
                ClientRecord.deleted_at.is_(None),
            )
            .order_by(ClientRecord.id.asc())
        )
        return self._legacy_list(query)

    def get_deleted_by_id_number(self, id_number: str) -> list[LegacyClientView]:
        """Retrieve deleted ClientRecords by ID number in legacy Client shape."""
        legacy_any = self.db.query(Client.id).filter(Client.id_number == id_number).first()
        if legacy_any:
            return (
                self._legacy_client_deleted_query()
                .filter(Client.id_number == id_number)
                .order_by(Client.deleted_at.desc())
                .all()
            )
        query = (
            self._legacy_query()
            .filter(
                LegalEntity.id_number == id_number,
                ClientRecord.deleted_at.isnot(None),
            )
            .order_by(ClientRecord.deleted_at.desc())
        )
        return self._legacy_list(query)

    def restore(self, client_id: int, restored_by: int) -> Optional[Client]:
        """Restore a soft-deleted client."""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client or client.deleted_at is None:
            return None
        client.deleted_at = None
        client.deleted_by = None
        client.restored_at = utcnow()
        client.restored_by = restored_by
        self.db.flush()
        return client

    def soft_delete(self, client_id: int, deleted_by: int) -> bool:
        """Soft-delete a client by setting deleted_at."""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return False
        client.deleted_at = utcnow()
        client.deleted_by = deleted_by
        self.db.flush()
        return True

    _SORTABLE_FIELDS = {
        "full_name": LegalEntity.official_name,
        "official_name": LegalEntity.official_name,
        "created_at": ClientRecord.created_at,
        "status": ClientRecord.status,
    }

    def _active_query(self):
        if self.db.query(Client.id).first():
            return self._legacy_client_active_query()
        return self._legacy_query().filter(ClientRecord.deleted_at.is_(None))

    def _apply_list_filters(self, query, search=None, status=None):
        if getattr(query.column_descriptions[0].get("entity"), "__name__", None) == "Client":
            if search:
                term = f"%{search.strip()}%"
                query = query.filter(
                    Client.full_name.ilike(term) | Client.id_number.ilike(term)
                )
            if status:
                query = query.filter(Client.status == status)
            return query
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
        """List active clients with optional search, status filter, and sorting."""
        query = self._apply_list_filters(self._active_query(), search, status)
        if getattr(query.column_descriptions[0].get("entity"), "__name__", None) == "Client":
            col = {
                "full_name": Client.full_name,
                "created_at": Client.created_at,
                "status": Client.status,
            }.get(sort_by, Client.full_name)
            query = query.order_by(desc(col) if sort_order == "desc" else asc(col))
            return self._paginate(query, page, page_size)
        if sort_by == "full_name":
            sort_by = "official_name"
        col = self._SORTABLE_FIELDS.get(sort_by, LegalEntity.official_name)
        query = query.order_by(desc(col) if sort_order == "desc" else asc(col))
        query = query.offset((page - 1) * page_size).limit(page_size)
        return self._legacy_list(query)

    def count(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
    ) -> int:
        """Count active clients with optional search and status filter."""
        query = self._apply_list_filters(self._active_query(), search, status)
        return query.count()

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LegacyClientView], int]:
        """Cross-domain search — used by search and tax_deadline domains."""
        q = self._active_query()
        if getattr(q.column_descriptions[0].get("entity"), "__name__", None) == "Client":
            if query:
                term = f"%{query.strip()}%"
                q = q.filter(Client.full_name.ilike(term) | Client.id_number.ilike(term))
            if client_name:
                q = q.filter(Client.full_name.ilike(f"%{client_name.strip()}%"))
            if id_number:
                q = q.filter(Client.id_number.ilike(f"%{id_number.strip()}%"))
            total = q.count()
            items = self._paginate(q.order_by(Client.full_name.asc()), page, page_size)
            return items, total
        if query:
            term = f"%{query.strip()}%"
            q = q.filter(LegalEntity.official_name.ilike(term) | LegalEntity.id_number.ilike(term))
        if client_name:
            q = q.filter(LegalEntity.official_name.ilike(f"%{client_name.strip()}%"))
        if id_number:
            q = q.filter(LegalEntity.id_number.ilike(f"%{id_number.strip()}%"))
        total = q.count()
        items = (
            q.order_by(LegalEntity.official_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return self._legacy_list(items), total

    def list_by_ids(self, client_ids: list[int]) -> list[LegacyClientView]:
        """Batch fetch clients by a list of IDs."""
        if not client_ids:
            return []
        legacy = (
            self._legacy_client_active_query()
            .filter(Client.id.in_(client_ids))
            .all()
        )
        if legacy:
            return legacy
        query = (
            self._legacy_query()
            .filter(ClientRecord.id.in_(client_ids), ClientRecord.deleted_at.is_(None))
        )
        return self._legacy_list(query)

    def list_all(self) -> list[LegacyClientView]:
        """List all active clients ordered by name."""
        legacy = self._legacy_client_active_query().order_by(Client.full_name.asc()).all()
        if legacy:
            return legacy
        query = self._active_query().order_by(LegalEntity.official_name.asc())
        return self._legacy_list(query)

    def update(self, client_id: int, **fields) -> Optional[Client]:
        """Update client identity fields."""
        client = self.get_by_id(client_id)
        return self._update_entity(client, **fields)

    def count_by_status(self) -> dict[ClientStatus, int]:
        """Count active (non-deleted) clients grouped by status."""
        if self.db.query(Client.id).first():
            rows = (
                self.db.query(Client.status, func.count(Client.id))
                .filter(Client.deleted_at.is_(None))
                .group_by(Client.status)
                .all()
            )
            return {status: count for status, count in rows}
        rows = (
            self.db.query(ClientRecord.status, func.count(ClientRecord.id))
            .filter(ClientRecord.deleted_at.is_(None))
            .group_by(ClientRecord.status)
            .all()
        )
        return {status: count for status, count in rows}

    def get_next_office_client_number(self) -> int:
        """Return the next office client number in ascending order."""
        current_max = self.db.query(func.max(Client.office_client_number)).scalar()
        return 1 if current_max is None else current_max + 1
