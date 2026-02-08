from sqlalchemy.orm import Session

from app.models import BinderStatus
from app.repositories import BinderRepository


class DashboardService:
    """Dashboard summary and metrics business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)

    def get_summary(self) -> dict:
        """
        Get dashboard summary counters.
        
        Returns:
            {
                "binders_in_office": int,
                "binders_ready_for_pickup": int,
                "binders_overdue": int
            }
        """
        return {
            "binders_in_office": self.binder_repo.count_by_status(BinderStatus.IN_OFFICE),
            "binders_ready_for_pickup": self.binder_repo.count_by_status(
                BinderStatus.READY_FOR_PICKUP
            ),
            "binders_overdue": self.binder_repo.count_by_status(BinderStatus.OVERDUE),
        }