from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import NotFoundError


class BinderOperationsService:
    """Operational binder queries."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = BinderRepository(db)

    def get_open_binders(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Binder], int]:
        """Get open binders with pagination."""
        items = self.repo.list_open_binders(page=page, page_size=page_size)
        total = self.repo.count_open_binders()
        return items, total

    def get_client_binders(
        self,
        client_record_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Binder], int]:
        """Get all binders for a client with pagination."""
        client_record = ClientRecordRepository(self.db).get_by_id(client_record_id)
        if not client_record:
            raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT_RECORD.NOT_FOUND")
        binders = self.repo.list_by_client_record(client_record_id)
        total = len(binders)
        offset = (page - 1) * page_size
        return binders[offset: offset + page_size], total

    def get_active_binder_for_client(self, client_record_id: int) -> Optional["Binder"]:
        """Return the active IN_OFFICE binder for a client, or None."""
        client_record = ClientRecordRepository(self.db).get_by_id(client_record_id)
        if not client_record:
            return None
        return self.repo.get_active_by_client_record(client_record_id)

    def map_active_binders_for_clients(self, client_record_ids: list[int]) -> dict[int, "Binder"]:
        """Return {client_record_id: binder} for each client's active IN_OFFICE binder."""
        return self.repo.map_active_by_clients(client_record_ids)

    def client_exists(self, client_record_id: int) -> bool:
        """Compatibility helper for callers that still query client existence here."""
        return ClientRecordRepository(self.db).get_by_id(client_record_id) is not None

    def enrich_binder(
        self,
        binder: Binder,
        reference_date: Optional[date] = None,
    ) -> dict:
        """
        Enrich binder with operational state.

        Returns a dict that matches BinderDetailResponse fields:
          id, client_record_id, office_client_number, client_name, client_id_number, binder_number, period_start, period_end,
          status, returned_at, pickup_person_name, days_in_office.
        """
        ref_date = reference_date or date.today()

        client_record = ClientRecordRepository(self.db).get_by_id(binder.client_record_id)
        legal_entity = (
            self.db.query(LegalEntity).filter(LegalEntity.id == client_record.legal_entity_id).first()
            if client_record
            else None
        )
        office_client_number = client_record.office_client_number if client_record else None
        client_name = legal_entity.official_name if legal_entity else None
        client_id_number = legal_entity.id_number if legal_entity else None

        # days_in_office is only defined once the binder has a derived period_start.
        days_in_office = (
            max(0, (ref_date - binder.period_start).days) if binder.period_start is not None else None
        )

        return {
            "id": binder.id,
            "client_record_id": binder.client_record_id,
            "office_client_number": office_client_number,
            "client_name": client_name,
            "client_id_number": client_id_number,
            "binder_number": binder.binder_number,
            "period_start": binder.period_start,
            "period_end": binder.period_end,
            "status": binder.status,
            "returned_at": binder.returned_at,
            "pickup_person_name": binder.pickup_person_name,
            "days_in_office": days_in_office,
        }
