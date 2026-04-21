from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.models.binder import BinderStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.users.models.user import UserRole
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService
from app.dashboard.services.dashboard_quick_actions_builder import build_quick_actions


class DashboardOverviewService:
    """ dashboard overview business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
        self.business_repo = BusinessRepository(db)
        self.reminder_repo = ReminderRepository(db)
        self.vat_repo = VatWorkItemRepository(db)
        self.annual_report_repo = AnnualReportRepository(db)
        self.extended_service = DashboardExtendedService(db)

    def get_overview(
        self,
        reference_date: Optional[date] = None,
        user_role: Optional[UserRole] = None,
    ) -> dict:
        if reference_date is None:
            reference_date = date.today()

        current_period = reference_date.strftime("%Y-%m")
        attention_items = self.extended_service.get_attention_items(user_role=user_role)
        quick_actions = self._build_quick_actions(user_role, current_period)
        return {
            "total_clients": self.business_repo.count(),
            "active_clients": self.client_record_repo.count(),
            "active_binders": self.binder_repo.count_active(),
            "binders_in_office": self.binder_repo.count_by_status(BinderStatus.IN_OFFICE),
            "binders_ready_for_pickup": self.binder_repo.count_by_status(BinderStatus.READY_FOR_PICKUP),
            "open_reminders": self.reminder_repo.count_pending_by_date(reference_date),
            "vat_due_this_month": self.vat_repo.count_by_period_not_filed(current_period),
            "quick_actions": quick_actions,
            "attention": {"items": attention_items, "total": len(attention_items)},
        }

    def _build_quick_actions(
        self,
        user_role: Optional[UserRole],
        current_period: str,
    ) -> list[dict]:
        return build_quick_actions(
            binder_repo=self.binder_repo,
            charge_repo=self.charge_repo,
            business_repo=self.business_repo,
            vat_repo=self.vat_repo,
            annual_report_repo=self.annual_report_repo,
            user_role=user_role,
            current_period=current_period,
        )
