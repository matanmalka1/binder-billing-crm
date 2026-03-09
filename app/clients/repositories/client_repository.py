from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.clients.models.client import Client, ClientStatus
from app.utils.time_utils import utcnow


class ClientRepository(BaseRepository):
    """Data access layer for Client entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        full_name: str,
        id_number: str,
        client_type: str,
        opened_at: date,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Client:
        """Create new client."""
        client = Client(
            full_name=full_name,
            id_number=id_number,
            client_type=client_type,
            opened_at=opened_at,
            phone=phone,
            email=email,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def get_by_id(self, client_id: int) -> Optional[Client]:
        """Retrieve client by ID (excludes soft-deleted)."""
        return (
            self.db.query(Client)
            .filter(Client.id == client_id, Client.deleted_at.is_(None))
            .first()
        )

    def get_by_id_number(self, id_number: str) -> Optional[Client]:
        """Retrieve client by ID number (excludes soft-deleted)."""
        return (
            self.db.query(Client)
            .filter(Client.id_number == id_number, Client.deleted_at.is_(None))
            .first()
        )

    def list(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> list[Client]:
        """List clients with optional filters. search matches full_name or id_number."""
        query = self.db.query(Client).filter(Client.deleted_at.is_(None))

        if status:
            query = query.filter(Client.status == status)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Client.full_name.ilike(term) | Client.id_number.ilike(term)
            )

        query = query.order_by(Client.opened_at.desc())
        return self._paginate(query, page, page_size)

    def count(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count clients with optional filters."""
        query = self.db.query(Client).filter(Client.deleted_at.is_(None))
        if status:
            query = query.filter(Client.status == status)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Client.full_name.ilike(term) | Client.id_number.ilike(term)
            )
        return query.count()

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Client], int]:
        """DB-level search returning (items, total)."""
        q = self.db.query(Client).filter(Client.deleted_at.is_(None))
        if query:
            term = f"%{query.strip()}%"
            q = q.filter(Client.full_name.ilike(term) | Client.id_number.ilike(term))
        if client_name:
            q = q.filter(Client.full_name.ilike(f"%{client_name.strip()}%"))
        if id_number:
            q = q.filter(Client.id_number.ilike(f"%{id_number.strip()}%"))
        total = q.count()
        items = self._paginate(q.order_by(Client.opened_at.desc()), page, page_size)
        return items, total

    def list_by_ids(self, client_ids: list[int]) -> list[Client]:
        """Batch fetch clients by a list of IDs (single query)."""
        if not client_ids:
            return []
        return self.db.query(Client).filter(Client.id.in_(client_ids)).all()

    def list_all(self, status: Optional[str] = None) -> list[Client]:
        """List all clients (optionally filtered by status)."""
        query = self.db.query(Client).filter(Client.deleted_at.is_(None))
        if status:
            query = query.filter(Client.status == status)
        return query.order_by(Client.full_name).all()

    def soft_delete(self, client_id: int, deleted_by: int) -> bool:
        """Soft-delete a client by setting deleted_at."""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return False
        client.deleted_at = utcnow()
        client.deleted_by = deleted_by
        self.db.commit()
        return True

    def update(self, client_id: int, **fields) -> Optional[Client]:
        """Update client fields."""
        client = self.get_by_id(client_id)
        return self._update_entity(client, **fields)

