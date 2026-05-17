"""Analytics, KPI, and overview service for AdvancePayment domain."""

from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import (
    AdvancePayment,
    AdvancePaymentStatus,
)
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    AdvancePaymentAggregationRepository,
)
from app.advance_payments.repositories.turnover_lookup_repository import (
    TurnoverLookupRepository,
)
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import NotFoundError


class AdvancePaymentAnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdvancePaymentAggregationRepository(db)

    @staticmethod
    def _collection_rate(total_paid: float, total_expected: float) -> float:
        return (
            round(total_paid / total_expected * 100, 2) if total_expected > 0 else 0.0
        )

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

        rows, total = self.repo.list_overview_payment_rows(
            year=year,
            month=month,
            statuses=statuses,
            page=page,
            page_size=page_size,
        )

        turnover_repo = TurnoverLookupRepository(self.db)
        payments = [row[0] for row in rows]
        live_turnover_map = self._build_live_turnover_map(payments, turnover_repo)

        return (
            [
                (
                    p,
                    office_client_number,
                    business_name,
                    id_number,
                    live_turnover_map.get((p.client_record_id, p.period)),
                    p.advance_rate,
                )
                for p, office_client_number, business_name, id_number in rows
            ],
            total,
        )

    @staticmethod
    def _build_live_turnover_map(
        payments: list[AdvancePayment],
        turnover_repo: TurnoverLookupRepository,
    ) -> dict[tuple[int, str], Optional[object]]:
        """Batch-fetch live turnover per (client_record_id, period)."""
        from collections import defaultdict

        by_client: dict[int, list[tuple[str, int]]] = defaultdict(list)
        for p in payments:
            if p.turnover_amount is None:
                by_client[p.client_record_id].append((p.period, p.period_months_count))

        result: dict[tuple[int, str], Optional[object]] = {}
        for client_id, period_list in by_client.items():
            turnover_by_period = turnover_repo.get_turnover_for_many(
                client_id, period_list
            )
            for period, (turnover, _) in turnover_by_period.items():
                result[(client_id, period)] = turnover
        return result

    # ─── KPIs ─────────────────────────────────────────────────────────────────

    def get_annual_kpis_for_client(self, client_record_id: int, year: int) -> dict:
        if not ClientRecordRepository(self.db).get_by_id(client_record_id):
            raise NotFoundError(
                f"רשומת לקוח {client_record_id} לא נמצאה",
                "ADVANCE_PAYMENT.CLIENT_NOT_FOUND",
            )
        data = self.repo.get_annual_kpis_for_client(client_record_id, year)
        return {
            **data,
            "client_record_id": client_record_id,
            "year": year,
            "collection_rate": self._collection_rate(
                data["total_paid"], data["total_expected"]
            ),
        }

    def get_overview_kpis(
        self,
        year: int,
        month: Optional[int] = None,
        statuses: Optional[list[AdvancePaymentStatus]] = None,
    ) -> dict:
        if statuses is None:
            statuses = list(AdvancePaymentStatus)
        data = self.repo.get_overview_kpis(year, month, statuses)
        return {
            **data,
            "collection_rate": self._collection_rate(
                data["total_paid"], data["total_expected"]
            ),
        }
