from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Client, ClientStatus
from app.repositories import ClientRepository


class ClientService:
    """Client management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)

    def create_client(
        self,
        full_name: str,
        id_number: str,
        client_type: str,
        opened_at: date,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Client:
        """Create new client. Raises ValueError if ID number exists."""
        existing = self.client_repo.get_by_id_number(id_number)
        if existing:
            raise ValueError(f"Client with ID number {id_number} already exists")

        return self.client_repo.create(
            full_name=full_name,
            id_number=id_number,
            client_type=client_type,
            opened_at=opened_at,
            phone=phone,
            email=email,
            notes=notes,
        )

    def get_client(self, client_id: int) -> Optional[Client]:
        """Get client by ID."""
        return self.client_repo.get_by_id(client_id)

    def list_clients(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Client], int]:
        """List clients with pagination. Returns (items, total)."""
        items = self.client_repo.list(status=status, page=page, page_size=page_size)
        total = self.client_repo.count(status=status)
        return items, total

    def update_client(self, client_id: int, **fields) -> Optional[Client]:
        """Update client fields."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            return None

        # Prevent updating status to closed without closed_at
        if "status" in fields and fields["status"] == ClientStatus.CLOSED:
            if "closed_at" not in fields:
                fields["closed_at"] = date.today()

        return self.client_repo.update(client_id, **fields)

    def freeze_client(self, client_id: int) -> Optional[Client]:
        """Freeze client."""
        return self.client_repo.set_status(client_id, ClientStatus.FROZEN)

    def close_client(self, client_id: int) -> Optional[Client]:
        """Close client permanently."""
        return self.update_client(client_id, status=ClientStatus.CLOSED, closed_at=date.today())