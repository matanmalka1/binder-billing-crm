"""Read-only queries for VatWorkItem entities."""

from typing import Optional

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

    def get_by_business_period(self, business_id: int, period: str) -> Optional[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.business_id == business_id,
                VatWorkItem.period == period,
                VatWorkItem.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_business(self, business_id: int, limit: int = 200) -> list[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.business_id == business_id,
                VatWorkItem.deleted_at.is_(None),
            )
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
        business_ids: Optional[list[int]] = None,
    ) -> list[VatWorkItem]:
        offset = (page - 1) * page_size
        q = (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.status == status, VatWorkItem.deleted_at.is_(None))
        )
        if period:
            q = q.filter(VatWorkItem.period == period)
        if business_ids is not None:
            q = q.filter(VatWorkItem.business_id.in_(business_ids))
        return q.order_by(VatWorkItem.period.desc()).offset(offset).limit(page_size).all()

    def count_by_status(
        self,
        status: VatWorkItemStatus,
        period: Optional[str] = None,
        business_ids: Optional[list[int]] = None,
    ) -> int:
        q = (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.status == status, VatWorkItem.deleted_at.is_(None))
        )
        if period:
            q = q.filter(VatWorkItem.period == period)
        if business_ids is not None:
            q = q.filter(VatWorkItem.business_id.in_(business_ids))
        return q.count()

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        period: Optional[str] = None,
        business_ids: Optional[list[int]] = None,
    ) -> list[VatWorkItem]:
        offset = (page - 1) * page_size
        q = self.db.query(VatWorkItem).filter(VatWorkItem.deleted_at.is_(None))
        if period:
            q = q.filter(VatWorkItem.period == period)
        if business_ids is not None:
            q = q.filter(VatWorkItem.business_id.in_(business_ids))
        return q.order_by(VatWorkItem.period.desc()).offset(offset).limit(page_size).all()

    def count_all(
        self,
        period: Optional[str] = None,
        business_ids: Optional[list[int]] = None,
    ) -> int:
        q = self.db.query(VatWorkItem).filter(VatWorkItem.deleted_at.is_(None))
        if period:
            q = q.filter(VatWorkItem.period == period)
        if business_ids is not None:
            q = q.filter(VatWorkItem.business_id.in_(business_ids))
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

    def sum_net_vat_by_business_year(self, business_id: int, tax_year: int) -> Optional[float]:
        row = (
            self.db.query(sa_func.sum(VatWorkItem.net_vat).label("total_vat"))
            .filter(
                VatWorkItem.business_id == business_id,
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
