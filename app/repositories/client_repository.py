from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Client, ClientStatus


class ClientRepository:
    """Data access layer for Client entities."""

    def __init__(self, db: Session):
        self.db = db

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
    ) -> list[Client]:
        """List clients with optional filters."""
        query = self.db.query(Client)

        if status:
            query = query.filter(Client.status == status)

        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()

    def count(self, status: Optional[str] = None) -> int:
        """Count clients with optional filters."""
        query = self.db.query(Client)
        if status:
            query = query.filter(Client.status == status)
        return query.count()

    def update(self, client_id: int, **fields) -> Optional[Client]:
        """Update client fields."""
        client = self.get_by_id(client_id)
        if not client:
            return None

        for key, value in fields.items():
            if hasattr(client, key):
                setattr(client, key, value)

        self.db.commit()
        self.db.refresh(client)
        return client

    def set_status(self, client_id: int, status: ClientStatus) -> Optional[Client]:
        """Set client status."""
        return self.update(client_id, status=status)