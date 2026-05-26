from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.annual_reports.repositories.annual_report_repository import (
    AnnualReportRepository,
)
from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.dashboard.services.advisor_today_service import AdvisorTodayService
from app.dashboard.services.dashboard_attention_service import DashboardAttentionService
from app.dashboard.services.dashboard_quick_actions_builder import build_quick_actions
from app.dashboard.services.recent_activity_service import RecentActivityService
from app.dashboard.services.tax_status_stats_service import TaxStatusStatsService
from app.notification.repositories.notification_repository import NotificationRepository
from app.users.models.user import UserRole
from app.utils.time_utils import israel_today


def _format_ils(amount: Decimal) -> str:
    try:
        normalized = amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        normalized = Decimal("0.00")
    formatted = f"{normalized:,.2f}".rstrip("0").rstrip(".")
    return f"₪{formatted}"


class DashboardOverviewService:
    """Dashboard overview — advisor gets full data, secretary gets operational subset."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
        self.business_repo = BusinessRepository(db)
        self.annual_report_repo = AnnualReportRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.attention_service = DashboardAttentionService(db)
        self.advisor_today_service = AdvisorTodayService(db)
        self.recent_activity_service = RecentActivityService(db)
        self.vat_stats_service = TaxStatusStatsService(db)

    def get_overview(
        self,
        reference_date: date | None = None,
        user_role: UserRole | None = None,
    ) -> dict:
        if reference_date is None:
            reference_date = israel_today()

        vat_stats = self.vat_stats_service.build(reference_date)

        is_advisor = user_role == UserRole.ADVISOR

        attention_items = (
            self.attention_service.build(user_role=user_role, reference_date=reference_date)
            if is_advisor
            else []
        )

        open_charges_count, open_charges_amount_ils = self._open_charges_stats(is_advisor)

        quick_actions = self._build_quick_actions(reference_date) if is_advisor else []
        advisor_today = (
            self.advisor_today_service.build(reference_date)
            if is_advisor
            else {"deadline_items": []}
        )

        has_clients = self.client_record_repo.count() > 0
        return {
            "is_empty": not has_clients,
            "open_charges_count": open_charges_count,
            "open_charges_amount_ils": open_charges_amount_ils,
            "vat_stats": vat_stats,
            "quick_actions": quick_actions,
            "attention": {
                "items": attention_items,
                "total": len(attention_items),
            },
            "advisor_today": advisor_today,
            "recent_activity": self.recent_activity_service.build() if is_advisor else [],
        }

    def _open_charges_stats(self, is_advisor: bool) -> tuple[int, str | None]:
        if not is_advisor:
            return 0, None
        count, total = self.charge_repo.open_charges_stats()
        if count == 0:
            return 0, None
        amount_ils = _format_ils(total) if total is not None else None
        return count, amount_ils

    def _build_quick_actions(self, today) -> list[dict]:
        return build_quick_actions(
            binder_repo=self.binder_repo,
            business_repo=self.business_repo,
            annual_report_repo=self.annual_report_repo,
            notification_repo=self.notification_repo,
            today=today,
        )
