from __future__ import annotations

from typing import Optional

from sqlalchemy import asc, desc, func

from app.common.repositories.base_repository import BaseRepository
from app.clients.models.client import Client
from app.clients.enums import ClientStatus
from app.clients.models.client import IdNumberType
from app.common.enums import EntityType, VatType
from app.utils.time_utils import utcnow


class ClientRepository(BaseRepository):
    """Data access layer for Client entities — identity only, no business logic."""

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

    def get_active_by_id_number(self, id_number: str) -> list[Client]:
        """Retrieve all active (non-deleted) clients with a given ID number."""
        return (
            self.db.query(Client)
            .filter(Client.id_number == id_number, Client.deleted_at.is_(None))
            .all()
        )

    def get_deleted_by_id_number(self, id_number: str) -> list[Client]:
        """Retrieve all soft-deleted clients by ID number, most recently deleted first."""
        return (
            self.db.query(Client)
            .filter(Client.id_number == id_number, Client.deleted_at.isnot(None))
            .order_by(Client.deleted_at.desc())
            .all()
        )

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
        "full_name": Client.full_name,
        "created_at": Client.created_at,
        "status": Client.status,
    }

    def _active_query(self):
        return self.db.query(Client).filter(Client.deleted_at.is_(None))

    def _apply_list_filters(self, query, search=None, status=None):
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Client.full_name.ilike(term) | Client.id_number.ilike(term)
            )
        if status:
            query = query.filter(Client.status == status)
        return query

    def list(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        sort_by: str = "full_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> list[Client]:
        """List active clients with optional search, status filter, and sorting."""
        query = self._apply_list_filters(self._active_query(), search, status)
        col = self._SORTABLE_FIELDS.get(sort_by, Client.full_name)
        query = query.order_by(desc(col) if sort_order == "desc" else asc(col))
        return self._paginate(query, page, page_size)

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
    ) -> tuple[list[Client], int]:
        """Cross-domain search — used by search and tax_deadline domains."""
        q = self._active_query()
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

    def list_by_ids(self, client_ids: list[int]) -> list[Client]:
        """Batch fetch clients by a list of IDs."""
        if not client_ids:
            return []
        return (
            self.db.query(Client)
            .filter(Client.id.in_(client_ids), Client.deleted_at.is_(None))
            .all()
        )

    def list_all(self) -> list[Client]:
        """List all active clients ordered by name."""
        return (
            self.db.query(Client)
            .filter(Client.deleted_at.is_(None))
            .order_by(Client.full_name.asc())
            .all()
        )

    def update(self, client_id: int, **fields) -> Optional[Client]:
        """Update client identity fields."""
        client = self.get_by_id(client_id)
        return self._update_entity(client, **fields)

    def count_by_status(self) -> dict[ClientStatus, int]:
        """Count active (non-deleted) clients grouped by status."""
        rows = (
            self.db.query(Client.status, func.count(Client.id))
            .filter(Client.deleted_at.is_(None))
            .group_by(Client.status)
            .all()
        )
        return {status: count for status, count in rows}

    def get_next_office_client_number(self) -> int:
        """Return the next office client number in ascending order."""
        current_max = self.db.query(func.max(Client.office_client_number)).scalar()
        return 1 if current_max is None else current_max + 1
