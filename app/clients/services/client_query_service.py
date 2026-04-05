"""Read-only client queries extracted to keep client_service.py under 150 lines."""

from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.clients.repositories.client_repository import ClientRepository


class ClientQueryService:
    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)

    def list_clients(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Client], int]:
        """List clients with pagination."""
        items = self.client_repo.list(search=search, page=page, page_size=page_size)
        total = self.client_repo.count(search=search)
        return items, total

    def list_all_clients(self) -> list[Client]:
        """Return all active clients."""
        return self.client_repo.list_all()

    def get_conflict_info(self, id_number: str) -> dict:
        """
        מחזיר מידע מלא על קונפליקטים לת.ז. נתונה.
        משמש את ה-router לבניית תגובת 409 מפורטת.
        """
        active = self.client_repo.get_active_by_id_number(id_number)
        deleted = self.client_repo.get_deleted_by_id_number(id_number)
        return {
            "active_clients": active,
            "deleted_clients": deleted,
        }
