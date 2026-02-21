from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.clients.models.client import Client, ClientStatus


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
        )
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def get_by_id(self, client_id: int) -> Optional[Client]:
        """Retrieve client by ID."""
        return self.db.query(Client).filter(Client.id == client_id).first()

    def get_by_id_number(self, id_number: str) -> Optional[Client]:
        """Retrieve client by ID number."""
        return self.db.query(Client).filter(Client.id_number == id_number).first()

    def list(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> list[Client]:
        """List clients with optional filters. search matches full_name or id_number."""
        query = self.db.query(Client)

        if status:
            query = query.filter(Client.status == status)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Client.full_name.ilike(term) | Client.id_number.ilike(term)
            )

        return self._paginate(query, page, page_size)

    def count(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count clients with optional filters."""
        query = self.db.query(Client)
        if status:
            query = query.filter(Client.status == status)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Client.full_name.ilike(term) | Client.id_number.ilike(term)
            )
        return query.count()

    def list_by_ids(self, client_ids: list[int]) -> list[Client]:
        """Batch fetch clients by a list of IDs (single query)."""
        if not client_ids:
            return []
        return self.db.query(Client).filter(Client.id.in_(client_ids)).all()

    def list_all(self, status: Optional[str] = None) -> list[Client]:
        """List all clients (optionally filtered by status)."""
        query = self.db.query(Client)
        if status:
            query = query.filter(Client.status == status)
        return query.order_by(Client.full_name).all()

    def update(self, client_id: int, **fields) -> Optional[Client]:
        """Update client fields."""
        client = self.get_by_id(client_id)
        return self._update_entity(client, **fields)

    def set_status(self, client_id: int, status: ClientStatus) -> Optional[Client]:
        """Set client status."""
        return self.update(client_id, status=status)
