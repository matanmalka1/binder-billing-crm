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
            ),
            "bimonthly": self._build_stat(
                VatType.BIMONTHLY,
                bimonthly_period,
                bimonthly_label,
            ),
        }

    def _build_stat(self, vat_type: VatType, period: str, label: str) -> dict:
        required = self.client_repo.count_active_by_vat_type(vat_type)
        submitted = self.vat_repo.count_filed_by_period_type(period, vat_type)
        pending = max(required - submitted, 0)
        percent = round((submitted / required) * 100) if required else 0
        return {
            "period": period,
            "period_label": label,
            "submitted": submitted,
            "required": required,
            "pending": pending,
            "completion_percent": percent,
        }
