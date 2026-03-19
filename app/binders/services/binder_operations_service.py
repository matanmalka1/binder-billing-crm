from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.binders.repositories.binder_repository_extensions import BinderRepositoryExtensions
from app.businesses.repositories.business_repository import BusinessRepository
from app.binders.services.work_state_service import WorkStateService
from app.binders.services.signals_service import SignalsService


class BinderOperationsService:
    """Operational binder queries."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = BinderRepositoryExtensions(db)
        self.business_repo = BusinessRepository(db)

    def get_open_binders(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Binder], int]:
        """Get open binders with pagination."""
        items = self.repo.list_open_binders(page=page, page_size=page_size)
        total = self.repo.count_open_binders()
        return items, total

    def get_business_binders(
        self,
        business_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Binder], int]:
        """Get all binders for a business with pagination."""
        items = self.repo.list_by_business(
            business_id=business_id,
            page=page,
            page_size=page_size,
        )
        total = self.repo.count_by_business(business_id)
        return items, total

    def business_exists(self, business_id: int) -> bool:
        """Check business existence for business-binders route."""
        return self.business_repo.get_by_id(business_id) is not None

    def enrich_binder(self, binder: Binder, db: Session | None = None) -> dict:
        """Enrich binder with operational state."""
        effective_db = db or self.db
        signals_service = SignalsService(effective_db)
        return {
            "id": binder.id,
            "business_id": binder.business_id,
            "binder_number": binder.binder_number,
            "status": binder.status.value,
            "received_at": binder.received_at,
            "returned_at": binder.returned_at,
            "pickup_person_name": binder.pickup_person_name,
            "work_state": WorkStateService.derive_work_state(binder, db=effective_db).value,
            "signals": signals_service.compute_binder_signals(binder),
        }
