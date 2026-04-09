"""Analytics, KPI, and overview service for AdvancePayment domain."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_analytics_repository import (
    AdvancePaymentAnalyticsRepository,
)
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    AdvancePaymentAggregationRepository,
)
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import NotFoundError


class AdvancePaymentAnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics_repo = AdvancePaymentAnalyticsRepository(db)
        self.aggregation_repo = AdvancePaymentAggregationRepository(db)

    @property
    def _business_repo(self) -> BusinessRepository:
        return BusinessRepository(self.db)

    @property
    def _client_repo(self) -> ClientRepository:
        return ClientRepository(self.db)

    @staticmethod
    def _collection_rate(total_paid: float, total_expected: float) -> float:
        return round(total_paid / total_expected * 100, 2) if total_expected > 0 else 0.0

    # ─── Overview ─────────────────────────────────────────────────────────────

    def list_overview(
        self,
        year: int,
        month: Optional[int] = None,
        statuses: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ):
        if statuses is None:
            statuses = list(AdvancePaymentStatus)

        payments = self.aggregation_repo.list_overview_payments(year, month, statuses)

        business_ids = list({p.business_id for p in payments})
        businesses = {b.id: b for b in self._business_repo.list_by_ids(business_ids)}

        rows = sorted(
            [
                (
                    p,
                    (businesses[p.business_id].business_name or businesses[p.business_id].client.full_name)
                    if p.business_id in businesses else "",
                    businesses[p.business_id].client_id if p.business_id in businesses else 0,
                )
                for p in payments
            ],
            key=lambda x: (x[1], x[0].period),
        )

        total = len(rows)
        offset = (page - 1) * page_size
        return rows[offset: offset + page_size], total

    # ─── KPIs ─────────────────────────────────────────────────────────────────

    def get_annual_kpis(self, business_id: int, year: int) -> dict:
        if not self._business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")
        data = self.analytics_repo.get_annual_kpis(business_id, year)
        return {
            **data,
            "business_id": business_id,
            "year": year,
            "collection_rate": self._collection_rate(data["total_paid"], data["total_expected"]),
        }

    def get_annual_kpis_for_client(self, client_id: int, year: int) -> dict:
        if not self._client_repo.get_by_id(client_id):
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "ADVANCE_PAYMENT.CLIENT_NOT_FOUND")
        data = self.analytics_repo.get_annual_kpis_for_client(client_id, year)
        return {
            **data,
            "client_id": client_id,
            "year": year,
            "collection_rate": self._collection_rate(data["total_paid"], data["total_expected"]),
        }

    def get_overview_kpis(
        self,
        year: int,
        month: Optional[int] = None,
        statuses: Optional[list[AdvancePaymentStatus]] = None,
    ) -> dict:
        if statuses is None:
            statuses = list(AdvancePaymentStatus)
        data = self.analytics_repo.get_overview_kpis(year, month, statuses)
        return {**data, "collection_rate": self._collection_rate(data["total_paid"], data["total_expected"])}

    def get_chart_data(self, business_id: int, year: int) -> dict:
        if not self._business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")
        months = self.analytics_repo.monthly_chart_data(business_id, year)
        return {"business_id": business_id, "year": year, "months": months}

    def get_chart_data_for_client(self, client_id: int, year: int) -> dict:
        if not self._client_repo.get_by_id(client_id):
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "ADVANCE_PAYMENT.CLIENT_NOT_FOUND")
        months = self.analytics_repo.monthly_chart_data_for_client(client_id, year)
        return {"client_id": client_id, "year": year, "months": months}
