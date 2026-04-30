from datetime import date

from sqlalchemy.orm import Session

from app.clients.repositories.client_vat_stats_repository import ClientVatStatsRepository
from app.common.enums import VatType
from app.dashboard.services.vat_dashboard_periods import (
    bimonthly_vat_period,
    monthly_vat_period,
)
from app.vat_reports.repositories.vat_work_item_stats_repository import (
    VatWorkItemStatsRepository,
)
from app.vat_reports.services.constants import VAT_STATUTORY_DEADLINE_DAY


class VatDashboardStatsService:
    def __init__(self, db: Session):
        self.client_repo = ClientVatStatsRepository(db)
        self.vat_repo = VatWorkItemStatsRepository(db)

    def build(self, reference_date: date) -> dict:
        monthly_period, monthly_label = monthly_vat_period(reference_date)
        bimonthly_period, bimonthly_label = bimonthly_vat_period(reference_date)
        return {
            "monthly": self._build_stat(
                VatType.MONTHLY,
                monthly_period,
                monthly_label,
                reference_date,
            ),
            "bimonthly": self._build_stat(
                VatType.BIMONTHLY,
                bimonthly_period,
                bimonthly_label,
                reference_date,
            ),
        }

    def _build_stat(
        self, vat_type: VatType, period: str, label: str, reference_date: date
    ) -> dict:
        required = self.client_repo.count_active_by_vat_type(vat_type)
        submitted = self.vat_repo.count_filed_by_period_type(period, vat_type)
        pending = max(required - submitted, 0)
        percent = round((submitted / required) * 100) if required else 0
        return {
            "period": period,
            "period_label": label,
            "status_label": self._status_label(
                period, vat_type, required, pending, reference_date
            ),
            "submitted": submitted,
            "required": required,
            "pending": pending,
            "completion_percent": percent,
        }

    def _status_label(
        self,
        period: str,
        vat_type: VatType,
        required: int,
        pending: int,
        reference_date: date,
    ) -> str:
        if required == 0:
            return "אין דוחות נדרשים"
        if pending == 0:
            return "הושלמה"
        due_date = self._due_date(period, vat_type)
        if reference_date > due_date:
            return "מועד הגשה עבר"
        return "ממתינה להגשה"

    def _due_date(self, period: str, vat_type: VatType) -> date:
        year, month = (int(part) for part in period.split("-", 1))
        offset = 2 if vat_type == VatType.BIMONTHLY else 1
        month_index = month - 1 + offset
        due_year = year + month_index // 12
        due_month = month_index % 12 + 1
        return date(due_year, due_month, VAT_STATUTORY_DEADLINE_DAY)
