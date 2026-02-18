from typing import Optional

from sqlalchemy.orm import Session

from app.models import BinderStatus, UserRole
from app.repositories import BinderRepository
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService


class DashboardService:
    """Dashboard summary and metrics business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.extended_service = DashboardExtendedService(db)

    def get_summary(self, user_role: Optional[UserRole] = None) -> dict:
        """
        Get dashboard summary counters.
        
        Returns:
            {
                "binders_in_office": int,
                "binders_ready_for_pickup": int,
                "binders_overdue": int,
                "attention": {"items": list, "total": int}
            }
        """
        attention_items = self.extended_service.get_attention_items(user_role=user_role)
        return {
            "binders_in_office": self.binder_repo.count_by_status(BinderStatus.IN_OFFICE),
            "binders_ready_for_pickup": self.binder_repo.count_by_status(
                BinderStatus.READY_FOR_PICKUP
            ),
            "binders_overdue": self.binder_repo.count_by_status(BinderStatus.OVERDUE),
            "attention": {"items": attention_items, "total": len(attention_items)},
        }
