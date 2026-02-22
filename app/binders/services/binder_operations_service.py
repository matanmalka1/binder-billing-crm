from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.binders.repositories.binder_repository_extensions import BinderRepositoryExtensions
from app.clients.repositories.client_repository import ClientRepository
from app.binders.services.work_state_service import WorkStateService
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

    def enrich_binder(self, binder: Binder, db: Session) -> dict:
        """Enrich binder with operational state."""
        signals_service = SignalsService(db)
        return {
            "id": binder.id,
            "client_id": binder.client_id,
            "binder_number": binder.binder_number,
            "status": binder.status.value,
            "received_at": binder.received_at,
            "returned_at": binder.returned_at,
            "pickup_person_name": binder.pickup_person_name,
            "work_state": WorkStateService.derive_work_state(binder, db=db).value,
            "signals": signals_service.compute_binder_signals(binder),
        }
