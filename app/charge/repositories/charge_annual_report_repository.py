"""Charge queries scoped to a specific annual report."""

from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.charge.models.charge import Charge, ChargeStatus


class ChargeAnnualReportRepository(BaseRepository):
    """Charge queries used by the annual_reports domain."""

    def __init__(self, db: Session):
        super().__init__(db)

    def list_by_annual_report(
        self,
        annual_report_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Charge], int]:
        """Return paginated charges linked to an annual report and their total count."""
        q = (
            self.db.query(Charge)
            .filter(
                Charge.annual_report_id == annual_report_id,
                Charge.deleted_at.is_(None),
            )
            .order_by(Charge.created_at.desc())
        )
        total = q.count()
        return self._paginate(q, page, page_size), total
