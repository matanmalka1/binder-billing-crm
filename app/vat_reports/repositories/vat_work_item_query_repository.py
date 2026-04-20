"""Read-only queries for VatWorkItem entities."""

from typing import Optional

from sqlalchemy import or_
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


class VatWorkItemQueryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, item_id: int) -> Optional[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.id == item_id, VatWorkItem.deleted_at.is_(None))
            .first()
        )

    def get_by_id_for_update(self, item_id: int) -> Optional[VatWorkItem]:
        """Fetch with a row-level lock for status transitions."""
        return (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.id == item_id, VatWorkItem.deleted_at.is_(None))
            .with_for_update()
            .first()
        )

    def get_by_client_record_period(self, client_record_id: int, period: str) -> Optional[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.period == period,
                VatWorkItem.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_client_record(self, client_record_id: int, limit: int = 200) -> list[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.period.desc())
            .limit(limit)
            .all()
        )

    def list_by_business_activity(self, business_activity_id: int, limit: int = 200) -> list[VatWorkItem]:
        """List work items that have at least one invoice tagged to this business activity."""
        from app.vat_reports.models.vat_invoice import VatInvoice
        return (
            self.db.query(VatWorkItem)
            .join(VatInvoice, VatInvoice.work_item_id == VatWorkItem.id)
            .filter(
                VatInvoice.business_activity_id == business_activity_id,
                VatWorkItem.deleted_at.is_(None),
            )
            .distinct()
            .order_by(VatWorkItem.period.desc())
            .limit(limit)
            .all()
        )

    def list_by_status(
        self,
        status: VatWorkItemStatus,
        page: int = 1,
        page_size: int = 20,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
    ) -> list[VatWorkItem]:
        offset = (page - 1) * page_size
        q = self.db.query(VatWorkItem).filter(
            VatWorkItem.status == status,
            VatWorkItem.deleted_at.is_(None),
        )
        if period:
            q = q.filter(VatWorkItem.period == period)
        if client_record_ids is not None:
            q = q.filter(VatWorkItem.client_record_id.in_(client_record_ids))
        return q.order_by(VatWorkItem.period.desc()).offset(offset).limit(page_size).all()

    def count_by_status(
        self,
        status: VatWorkItemStatus,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
    ) -> int:
        q = self.db.query(VatWorkItem).filter(
            VatWorkItem.status == status,
            VatWorkItem.deleted_at.is_(None),
        )
        if period:
            q = q.filter(VatWorkItem.period == period)
        if client_record_ids is not None:
            q = q.filter(VatWorkItem.client_record_id.in_(client_record_ids))
        return q.count()

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
    ) -> list[VatWorkItem]:
        offset = (page - 1) * page_size
        q = self.db.query(VatWorkItem).filter(VatWorkItem.deleted_at.is_(None))
        if period:
            q = q.filter(VatWorkItem.period == period)
        if client_record_ids is not None:
            q = q.filter(VatWorkItem.client_record_id.in_(client_record_ids))
        return q.order_by(VatWorkItem.period.desc()).offset(offset).limit(page_size).all()

    def count_all(
        self,
        period: Optional[str] = None,
        client_record_ids: Optional[list[int]] = None,
    ) -> int:
        q = self.db.query(VatWorkItem).filter(VatWorkItem.deleted_at.is_(None))
        if period:
            q = q.filter(VatWorkItem.period == period)
        if client_record_ids is not None:
            q = q.filter(VatWorkItem.client_record_id.in_(client_record_ids))
        return q.count()

    def count_by_period_not_filed(self, period: str) -> int:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.period == period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
            )
            .count()
        )

    def sum_net_vat_by_client_record_year(self, client_record_id: int, tax_year: int) -> Optional[float]:
        row = (
            self.db.query(sa_func.sum(VatWorkItem.net_vat).label("total_vat"))
            .filter(
                VatWorkItem.client_record_id == client_record_id,
                sa_func.substr(VatWorkItem.period, 1, 4) == str(tax_year),
                VatWorkItem.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return float(row[0]) if row and row[0] is not None else None

    def list_not_filed_for_period(self, period: str, limit: int = 3) -> list[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.period == period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.created_at.asc())
            .limit(limit)
            .all()
        )
