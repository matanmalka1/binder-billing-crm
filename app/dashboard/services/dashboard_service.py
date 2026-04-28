from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import BinderStatus
from app.clients.enums import ClientStatus
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.users.models.user import UserRole
from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService
from app.dashboard.services.vat_dashboard_stats_service import VatDashboardStatsService


class DashboardService:
    """Dashboard summary and metrics business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
        self.business_repo = BusinessRepository(db)
        self.reminder_repo = ReminderRepository(db)
        self.extended_service = DashboardExtendedService(db)
        self.vat_stats_service = VatDashboardStatsService(db)

    def get_summary(self, user_role: Optional[UserRole] = None) -> dict:
        today = date.today()
        attention_items = self.extended_service.get_attention_items(user_role=user_role)
        return {
            "total_clients": self.business_repo.count(),
            "active_clients": self.client_record_repo.count(status=ClientStatus.ACTIVE),
            "binders_in_office": self.binder_repo.count_by_status(BinderStatus.IN_OFFICE),
            "binders_ready_for_pickup": self.binder_repo.count_by_status(
                BinderStatus.READY_FOR_PICKUP
            ),
            "open_reminders": self.reminder_repo.count_pending_by_date(today),
            "vat_stats": self.vat_stats_service.build(today),
            "attention": {"items": attention_items, "total": len(attention_items)},
        }
