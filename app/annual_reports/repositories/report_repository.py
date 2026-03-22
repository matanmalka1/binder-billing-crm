"""Repository operations for the AnnualReport entity."""

from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.annual_reports.models import AnnualReport, AnnualReportStatus
from app.utils.time_utils import utcnow

_SORT_COLUMNS = {
    "tax_year": AnnualReport.tax_year,
    "status": AnnualReport.status,
    "filing_deadline": AnnualReport.filing_deadline,
    "created_at": AnnualReport.created_at,
    "business_id": AnnualReport.business_id,
}


def _sort_col(sort_by: str, order: str):
    col = _SORT_COLUMNS.get(sort_by, AnnualReport.created_at)
    return col.asc() if order == "asc" else col.desc()

class AnnualReportReportRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    # ── AnnualReport CRUD / queries ─────────────────────────────────────────

    def create(self, **kwargs) -> AnnualReport:
        report = AnnualReport(**kwargs)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_by_id(self, report_id: int) -> Optional[AnnualReport]:
        return (
            self.db.query(AnnualReport)
            .filter(AnnualReport.id == report_id, AnnualReport.deleted_at.is_(None))
            .first()
        )

    def get_by_business_year(self, business_id: int, tax_year: int) -> Optional[AnnualReport]:
        return (
            self.db.query(AnnualReport)
            .filter(
                AnnualReport.business_id == business_id,
                AnnualReport.tax_year == tax_year,
                AnnualReport.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_business(self, business_id: int, page: int = 1, page_size: int = 20) -> list[AnnualReport]:
        q = (
            self.db.query(AnnualReport)
            .filter(AnnualReport.business_id == business_id, AnnualReport.deleted_at.is_(None))
            .order_by(AnnualReport.tax_year.desc())
        )
        return self._paginate(q, page, page_size)

    def count_by_business(self, business_id: int) -> int:
        return (
            self.db.query(AnnualReport)
            .filter(AnnualReport.business_id == business_id, AnnualReport.deleted_at.is_(None))
            .count()
        )

    def list_by_status(
        self,
        status: AnnualReportStatus,
        tax_year: Optional[int] = None,
        assigned_to: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AnnualReport]:
        q = self.db.query(AnnualReport).filter(AnnualReport.status == status, AnnualReport.deleted_at.is_(None))
        if tax_year:
            q = q.filter(AnnualReport.tax_year == tax_year)
        if assigned_to:
            q = q.filter(AnnualReport.assigned_to == assigned_to)
        q = q.order_by(AnnualReport.filing_deadline.asc())
        return self._paginate(q, page, page_size)

    def count_by_status(
        self,
        status: AnnualReportStatus,
        tax_year: Optional[int] = None,
    ) -> int:
        q = self.db.query(AnnualReport).filter(AnnualReport.status == status, AnnualReport.deleted_at.is_(None))
        if tax_year:
            q = q.filter(AnnualReport.tax_year == tax_year)
        return q.count()

    def list_by_tax_year(
        self,
        tax_year: int,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "status",
        order: str = "asc",
    ) -> list[AnnualReport]:
        q = (
            self.db.query(AnnualReport)
            .filter(AnnualReport.tax_year == tax_year, AnnualReport.deleted_at.is_(None))
            .order_by(_sort_col(sort_by, order))
        )
        return self._paginate(q, page, page_size)

    def count_by_tax_year(self, tax_year: int) -> int:
        return self.db.query(AnnualReport).filter(
            AnnualReport.tax_year == tax_year, AnnualReport.deleted_at.is_(None)
        ).count()

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "tax_year",
        order: str = "desc",
    ) -> list[AnnualReport]:
        q = (
            self.db.query(AnnualReport)
            .filter(AnnualReport.deleted_at.is_(None))
            .order_by(_sort_col(sort_by, order))
        )
        return self._paginate(q, page, page_size)

    def list_all_with_businesses(self) -> list[AnnualReport]:
        """Return all non-deleted reports ordered for Kanban view."""
        return (
            self.db.query(AnnualReport)
            .filter(AnnualReport.deleted_at.is_(None))
            .order_by(AnnualReport.filing_deadline.asc().nulls_last(), AnnualReport.id.asc())
            .all()
        )

    def count_all(self) -> int:
        return self.db.query(AnnualReport).filter(AnnualReport.deleted_at.is_(None)).count()

    def list_by_tax_year_with_client(self, tax_year: int) -> list:
        """Return (AnnualReport, Business.client_id, Client.full_name) for status report."""
        from app.businesses.models.business import Business
        from app.clients.models.client import Client

        return (
            self.db.query(AnnualReport, Business.client_id, Client.full_name)
            .join(Business, Business.id == AnnualReport.business_id)
            .join(Client, Client.id == Business.client_id)
            .filter(
                AnnualReport.tax_year == tax_year,
                AnnualReport.deleted_at.is_(None),
                Business.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
            .order_by(AnnualReport.filing_deadline.asc().nulls_last())
            .all()
        )

    def update(self, report_id: int, **fields) -> Optional[AnnualReport]:
        report = self.get_by_id(report_id)
        return self._update_entity(report, touch_updated_at=True, **fields)

    def soft_delete(self, report_id: int, deleted_by: int) -> bool:
        report = self.get_by_id(report_id)
        if not report:
            return False
        report.deleted_at = utcnow()
        report.deleted_by = deleted_by
        self.db.commit()
        return True