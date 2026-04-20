"""Read-only client queries extracted to keep client_service.py under 150 lines."""

from typing import Optional

from sqlalchemy.orm import Session

from app.clients.enums import ClientStatus
from app.clients.repositories.client_repository import LegacyClientView
from app.clients.repositories.client_repository import ClientRepository
from app.clients.schemas.client import ClientListStats


class ClientQueryService:
    def __init__(self, db: Session):
        self.client_repo = ClientRepository(db)

    def list_clients(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        sort_by: str = "full_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LegacyClientView], int]:
        """List clients with pagination, optional status filter, and sorting."""
        items = self.client_repo.list(
            search=search,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        total = self.client_repo.count(search=search, status=status)
        return items, total

    def get_client_stats(self) -> ClientListStats:
        counts = self.client_repo.count_by_status()
        return ClientListStats(
            active=counts.get(ClientStatus.ACTIVE, 0),
            frozen=counts.get(ClientStatus.FROZEN, 0),
            closed=counts.get(ClientStatus.CLOSED, 0),
        )

    def list_all_clients(self) -> list[LegacyClientView]:
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
