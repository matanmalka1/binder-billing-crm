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
from app.vat_reports.repositories.vat_work_item_filters import (
    apply_vat_work_item_filters,
)

_FILED_STATUSES = {
    VatWorkItemStatus.FILED,
    VatWorkItemStatus.CANCELED,
}


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
        from app.vat_reports.models.vat_invoice import VatInvoice

        return self.db.scalars(
            select(VatWorkItem)
            .join(VatInvoice, VatInvoice.work_item_id == VatWorkItem.id)
            .where(
                VatInvoice.business_activity_id == business_activity_id,
                VatWorkItem.deleted_at.is_(None),
            )
            .distinct()
            .order_by(VatWorkItem.period.desc())
            .limit(limit)
        ).all()

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
        row = self.db.execute(
            select(func.sum(VatWorkItem.net_vat).label("total_vat")).where(
                VatWorkItem.client_record_id == client_record_id,
                func.substr(VatWorkItem.period, 1, 4) == str(tax_year),
                VatWorkItem.deleted_at.is_(None),
            )
        ).one_or_none()
        return float(row[0]) if row and row[0] is not None else None

    def list_not_filed_for_period(
        self, period: str, limit: int = 3
    ) -> list[VatWorkItem]:
        return self.db.scalars(
            scope_to_active_clients_stmt(select(VatWorkItem), VatWorkItem)
            .where(
                VatWorkItem.period == period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.created_at.asc())
            .limit(limit)
        ).all()

    def list_open_up_to_period(
        self, up_to_period: str, limit: int = 50
    ) -> list[VatWorkItem]:
        return self.db.scalars(
            scope_to_active_clients_stmt(select(VatWorkItem), VatWorkItem)
            .where(
                VatWorkItem.period <= up_to_period,
                VatWorkItem.status.notin_(list(_FILED_STATUSES)),
                VatWorkItem.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.period.asc())
            .limit(limit)
        ).all()
