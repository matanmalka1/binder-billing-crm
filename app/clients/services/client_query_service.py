"""Read-only client queries extracted to keep client_service.py under 150 lines."""

from typing import Optional

from sqlalchemy.orm import Session

from app.clients.enums import ClientStatus
from app.clients.repositories.client_record_read_repository import (
    get_full_record,
    get_full_record_including_deleted,
    get_full_records_bulk,
)
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRecordView, ClientRepository
from app.clients.schemas.client import ClientListStats
from app.clients.schemas.client_record_response import (
    ClientRecordListResponse,
    ClientRecordListStats,
    ClientRecordResponse,
)
from app.clients.services.client_enrichment_service import ClientEnrichmentService
from app.core.exceptions import NotFoundError


class ClientQueryService:
    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self.record_repo = ClientRecordRepository(db)

    def list_clients(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        sort_by: str = "full_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ClientRecordView], int]:
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

    def list_all_clients(self) -> list[ClientRecordView]:
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

    def get_full_client(self, client_record_id: int) -> ClientRecordResponse:
        data = get_full_record(self.db, client_record_id)
        if not data:
            raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT.NOT_FOUND")
        return ClientEnrichmentService(self.db).enrich_single(ClientRecordResponse(**data))

    def get_full_client_including_deleted(self, client_record_id: int) -> ClientRecordResponse:
        data = get_full_record_including_deleted(self.db, client_record_id)
        if not data:
            raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT.NOT_FOUND")
        return ClientRecordResponse(**data)

    def list_full_clients(
        self,
        search: Optional[str] = None,
        status: Optional[ClientStatus] = None,
        accountant_id: Optional[int] = None,
        sort_by: str = "official_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> ClientRecordListResponse:
        records = self.record_repo.list(
            search=search,
            status=status,
            accountant_id=accountant_id,
            sort_by="official_name" if sort_by == "full_name" else sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        total = self.record_repo.count(search=search, status=status, accountant_id=accountant_id)
        record_ids = [r.id for r in records]
        full_map = get_full_records_bulk(self.db, record_ids)
        items = [ClientRecordResponse(**full_map[rid]) for rid in record_ids if rid in full_map]
        items = ClientEnrichmentService(self.db).enrich_list(items)
        counts = self.record_repo.count_by_status()
        stats = ClientRecordListStats(
            active=counts.get(ClientStatus.ACTIVE, 0),
            frozen=counts.get(ClientStatus.FROZEN, 0),
            closed=counts.get(ClientStatus.CLOSED, 0),
        )
        return ClientRecordListResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            stats=stats,
        )
