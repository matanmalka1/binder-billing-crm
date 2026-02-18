from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Binder
from app.binders.repositories.binder_repository_extensions import BinderRepositoryExtensions  # FIXED: was app.repositories.binder_repository_extensions
from app.clients.repositories.client_repository import ClientRepository
from app.binders.services.sla_service import SLAService
from app.binders.services.work_state_service import WorkStateService
from app.binders.services.signals_service import SignalsService


class BinderOperationsService:
    """Sprint 2 operational binder queries with SLA enrichment."""

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

    def get_overdue_binders(
        self,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[Binder], int]:
        """Get overdue binders with pagination."""
        if reference_date is None:
            reference_date = date.today()

        items = self.repo.list_overdue_candidates(
            reference_date=reference_date,
            page=page,
            page_size=page_size,
        )
        total = self.repo.count_overdue_candidates(reference_date)
        return items, total

    def get_due_today_binders(
        self,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[Binder], int]:
        """Get binders due today with pagination."""
        if reference_date is None:
            reference_date = date.today()

        items = self.repo.list_due_today(
            reference_date=reference_date,
            page=page,
            page_size=page_size,
        )
        total = self.repo.count_due_today(reference_date)
        return items, total

    def get_client_binders(
        self,
        client_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Binder], int]:
        """Get all binders for a client with pagination."""
        items = self.repo.list_by_client(
            client_id=client_id,
            page=page,
            page_size=page_size,
        )
        total = self.repo.count_by_client(client_id)
        return items, total

    def client_exists(self, client_id: int) -> bool:
        """Check client existence for client-binders route."""
        return self.client_repo.get_by_id(client_id) is not None

    def enrich_binder_with_sla(self, binder: Binder, db: Session) -> dict:
        """
        Enrich binder with SLA and operational state.

        Sprint 6: Pass db session to WorkStateService for notification history.
        """
        signals_service = SignalsService(db)
        return {
            "id": binder.id,
            "client_id": binder.client_id,
            "binder_number": binder.binder_number,
            "status": binder.status.value,
            "received_at": binder.received_at,
            "expected_return_at": binder.expected_return_at,
            "returned_at": binder.returned_at,
            "pickup_person_name": binder.pickup_person_name,
            "is_overdue": SLAService.is_overdue(binder),
            "days_overdue": SLAService.days_overdue(binder),
            "work_state": WorkStateService.derive_work_state(binder, db=db).value,
            "signals": signals_service.compute_binder_signals(binder),
        }