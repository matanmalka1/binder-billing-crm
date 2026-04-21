"""Analytics, KPI, and overview service for AdvancePayment domain."""

from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_analytics_repository import (
    AdvancePaymentAnalyticsRepository,
)
from app.advance_payments.repositories.advance_payment_aggregation_repository import (
    AdvancePaymentAggregationRepository,
)
from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import NotFoundError


class AdvancePaymentAnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics_repo = AdvancePaymentAnalyticsRepository(db)
        self.aggregation_repo = AdvancePaymentAggregationRepository(db)

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

        client_record_ids = list({p.client_record_id for p in payments})
        records = {
            record.id: record for record in ClientRecordRepository(self.db).list_by_ids(client_record_ids)
        }
        legal_entity_ids = list({record.legal_entity_id for record in records.values()})
        legal_entities = {
            entity.id: entity
            for entity in self.db.query(LegalEntity).filter(LegalEntity.id.in_(legal_entity_ids)).all()
        } if legal_entity_ids else {}

        rows = sorted(
            [
                (
                    p,
                    records[p.client_record_id].office_client_number if p.client_record_id in records else None,
                    legal_entities[records[p.client_record_id].legal_entity_id].official_name
                    if p.client_record_id in records and records[p.client_record_id].legal_entity_id in legal_entities
                    else "",
                )
                for p in payments
            ],
            key=lambda x: (x[2], x[0].period),
        )

        total = len(rows)
        offset = (page - 1) * page_size
        return rows[offset: offset + page_size], total

    # ─── KPIs ─────────────────────────────────────────────────────────────────

    def get_annual_kpis_for_client(self, client_record_id: int, year: int) -> dict:
        if not ClientRecordRepository(self.db).get_by_id(client_record_id):
            raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "ADVANCE_PAYMENT.CLIENT_NOT_FOUND")
        data = self.analytics_repo.get_annual_kpis_for_client(client_record_id, year)
        return {
            **data,
            "client_record_id": client_record_id,
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

    def get_chart_data_for_client(self, client_record_id: int, year: int) -> dict:
        if not ClientRecordRepository(self.db).get_by_id(client_record_id):
            raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "ADVANCE_PAYMENT.CLIENT_NOT_FOUND")
        months = self.analytics_repo.monthly_chart_data_for_client(client_record_id, year)
        return {"client_record_id": client_record_id, "year": year, "months": months}
