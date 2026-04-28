from sqlalchemy.orm import Session

from app.common.enums import VatType
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


class VatWorkItemStatsRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_filed_by_period_type(self, period: str, vat_type: VatType) -> int:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.period == period,
                VatWorkItem.period_type == vat_type,
                VatWorkItem.status == VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
            )
            .count()
        )
