from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.repositories.annual_report_repository import (
    AnnualReportRepository,
)
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.models.binder import BinderStatus
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.notification.repositories.notification_repository import NotificationRepository
from app.users.models.user import UserRole
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService
from app.dashboard.services.dashboard_quick_actions_builder import build_quick_actions
from app.dashboard.services.advisor_today_service import AdvisorTodayService
from app.dashboard.services.tax_status_stats_service import TaxStatusStatsService
from app.utils.time_utils import israel_today


class DashboardOverviewService:
    """Dashboard overview — advisor gets full data, secretary gets operational subset."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
        self.business_repo = BusinessRepository(db)
        self.vat_repo = VatWorkItemRepository(db)
        self.annual_report_repo = AnnualReportRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.extended_service = DashboardExtendedService(db)
        self.advisor_today_service = AdvisorTodayService(db)
        self.vat_stats_service = TaxStatusStatsService(db)

    def get_overview(
        self,
        reference_date: Optional[date] = None,
        user_role: Optional[UserRole] = None,
    ) -> dict:
        if reference_date is None:
            reference_date = israel_today()

        vat_stats = self.vat_stats_service.build(reference_date)
        attention_data = self.extended_service.get_attention_data(
            user_role=user_role, reference_date=reference_date
        )

        is_advisor = user_role == UserRole.ADVISOR
        quick_actions = self._build_quick_actions(reference_date) if is_advisor else []
        advisor_today = (
            self.advisor_today_service.build(reference_date)
            if is_advisor
            else {"deadline_items": []}
        )
        attention_empty_checks = []
        if is_advisor and attention_data["open_charges_count"] == 0:
            attention_empty_checks = [
                {"key": "open_charges", "label": "אין חיובים פתוחים"}
            ]

        has_clients = self.client_record_repo.count() > 0
        return {
            "is_empty": not has_clients,
            "binders_in_office": self.binder_repo.count_by_status(
                BinderStatus.IN_OFFICE
            ),
            "binders_ready_for_pickup": self.binder_repo.count_by_status(
                BinderStatus.READY_FOR_PICKUP
            ),
            "open_charges_count": attention_data["open_charges_count"],
            "open_charges_amount_ils": attention_data["open_charges_amount_ils"],
            "vat_stats": vat_stats,
            "quick_actions": quick_actions,
            "attention": {
                "items": attention_data["items"],
                "total": len(attention_data["items"]),
            },
            "advisor_today": advisor_today,
            "attention_empty_checks": attention_empty_checks,
        }

    def _build_quick_actions(self, today) -> list[dict]:
        return build_quick_actions(
            binder_repo=self.binder_repo,
            business_repo=self.business_repo,
            vat_repo=self.vat_repo,
            annual_report_repo=self.annual_report_repo,
            notification_repo=self.notification_repo,
            today=today,
        )
