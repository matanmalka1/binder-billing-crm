from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import BinderStatus
from app.users.models.user import UserRole
from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService


class DashboardService:
    """Dashboard summary and metrics business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.business_repo = BusinessRepository(db)
        self.reminder_repo = ReminderRepository(db)
        self.vat_repo = VatWorkItemRepository(db)
        self.extended_service = DashboardExtendedService(db)

    def get_summary(self, user_role: Optional[UserRole] = None) -> dict:
        today = date.today()
        current_period = today.strftime("%Y-%m")
        attention_items = self.extended_service.get_attention_items(user_role=user_role)
        return {
            "total_clients": self.business_repo.count(),
            "binders_in_office": self.binder_repo.count_by_status(BinderStatus.IN_OFFICE),
            "binders_ready_for_pickup": self.binder_repo.count_by_status(
                BinderStatus.READY_FOR_PICKUP
            ),
            "open_reminders": self.reminder_repo.count_pending_by_date(today),
            "vat_due_this_month": self.vat_repo.count_by_period_not_filed(current_period),
            "attention": {"items": attention_items, "total": len(attention_items)},
        }
