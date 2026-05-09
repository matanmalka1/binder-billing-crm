"""Read-only queries for VatWorkItem entities."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.enums import VatType
from app.clients.models.client_record import ClientRecord
from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.repositories.base_repository import BaseRepository
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories import vat_work_item_extra_queries as extra_queries
from app.vat_reports.repositories.vat_work_item_filters import (
    apply_vat_work_item_filters,
)


class VatWorkItemQueryRepository(BaseRepository[VatWorkItem]):
    model = VatWorkItem

    def __init__(self, db: Session):
        super().__init__(db)

    def _query(self, status: Optional[VatWorkItemStatus] = None):
        stmt = scope_to_active_clients_stmt(
            select(VatWorkItem),
            VatWorkItem,
        ).where(VatWorkItem.deleted_at.is_(None))
        return stmt.where(VatWorkItem.status == status) if status is not None else stmt

    def _filtered_query(
        self,
        status: Optional[VatWorkItemStatus] = None,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
        period_type: Optional[VatType] = None,
    ):
        return apply_vat_work_item_filters(
            self._query(status),
            period=period,
            client_record_ids=client_record_ids,
            period_type=period_type,
        )

    def get_by_client_record_period(
        self, client_record_id: int, period: str
    ) -> Optional[VatWorkItem]:
        return self.db.scalars(
            select(VatWorkItem).where(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.period == period,
                VatWorkItem.deleted_at.is_(None),
            )
        ).first()

    def list_by_client_record(
        self, client_record_id: int, limit: int = 200
    ) -> list[VatWorkItem]:
        return self.db.scalars(
            select(VatWorkItem)
            .where(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.period.desc())
            .limit(limit)
        ).all()

    def list_by_business_activity(
        self, business_activity_id: int, limit: int = 200
    ) -> list[VatWorkItem]:
        return extra_queries.list_by_business_activity(
            self.db, business_activity_id, limit
        )

    def list_by_status(
        self,
        status: VatWorkItemStatus,
        page: int = 1,
        page_size: int = 20,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
        period_type: Optional[VatType] = None,
    ) -> list[VatWorkItem]:
        stmt = self._filtered_query(status, period, client_record_ids, period_type)
        stmt = self.apply_pagination(
            stmt.order_by(VatWorkItem.period.desc()), page, page_size
        )
        return list(self.db.scalars(stmt).all())

    def count_by_status(
        self,
        status: VatWorkItemStatus,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
        period_type: Optional[VatType] = None,
    ) -> int:
        stmt = self._filtered_query(status, period, client_record_ids, period_type)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return self.db.scalar(count_stmt)

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
        period_type: Optional[VatType] = None,
    ) -> list[VatWorkItem]:
        stmt = self._filtered_query(None, period, client_record_ids, period_type)
        stmt = self.apply_pagination(
            stmt.order_by(VatWorkItem.period.desc()), page, page_size
        )
        return list(self.db.scalars(stmt).all())

    def count_all(
        self,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
        period_type: Optional[VatType] = None,
    ) -> int:
        stmt = self._filtered_query(None, period, client_record_ids, period_type)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return self.db.scalar(count_stmt)

    def count_by_period_not_filed(self, period: str) -> int:
        return self.db.scalar(
            select(func.count(VatWorkItem.id))
            .join(ClientRecord, ClientRecord.id == VatWorkItem.client_record_id)
            .where(
                VatWorkItem.period == period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
                ClientRecord.deleted_at.is_(None),
            )
        )

    def sum_net_vat_by_client_record_year(
        self, client_record_id: int, tax_year: int
    ) -> Optional[float]:
        return extra_queries.sum_net_vat_by_client_record_year(
            self.db, client_record_id, tax_year
        )

    def list_not_filed_for_period(
        self, period: str, limit: int = 3
    ) -> list[VatWorkItem]:
        return extra_queries.list_not_filed_for_period(self.db, period, limit)

    def list_open_up_to_period(
        self, up_to_period: str, limit: int = 50
    ) -> list[VatWorkItem]:
        return extra_queries.list_open_up_to_period(self.db, up_to_period, limit)
