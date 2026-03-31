from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.binders.repositories.binder_repository_extensions import BinderRepositoryExtensions
from app.clients.repositories.client_repository import ClientRepository
from app.binders.services.signals_service import SignalsService


class BinderOperationsService:
    """Operational binder queries."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = BinderRepositoryExtensions(db)
        self.client_repo = ClientRepository(db)

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
        client_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Binder], int]:
        """Get all binders for a client with pagination."""
        items = self.repo.list_by_client(client_id=client_id, page=page, page_size=page_size)
        total = self.repo.count_by_client(client_id)
        return items, total

    def client_exists(self, client_id: int) -> bool:
        """Check client existence for client-binders route."""
        return self.client_repo.get_by_id(client_id) is not None

    def enrich_binder(
        self,
        binder: Binder,
        reference_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Enrich binder with operational state.

        Returns a dict that matches BinderDetailResponse fields:
          id, client_id, client_name, binder_number, period_start, period_end,
          status, returned_at, pickup_person_name, days_active, signals.
        """
        effective_db = db or self.db
        ref_date = reference_date or date.today()
        signals_service = SignalsService(effective_db)

        client = self.client_repo.get_by_id(binder.client_id)
        client_name = client.full_name if client else None

        # days_active = days elapsed since period_start (matches BinderDetailResponse).
        days_active = (ref_date - binder.period_start).days

        return {
            "id": binder.id,
            "client_id": binder.client_id,
            "client_name": client_name,
            "binder_number": binder.binder_number,
            "period_start": binder.period_start,
            "period_end": binder.period_end,
            "status": binder.status.value,
            "returned_at": binder.returned_at,
            "pickup_person_name": binder.pickup_person_name,
            "days_active": days_active,
            "signals": signals_service.compute_binder_signals(binder, ref_date),
        }
