"""Repository operations for the AnnualReport entity."""

from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.annual_reports.models import AnnualReport, AnnualReportStatus
from app.clients.models.client import Client
from app.utils.time import utcnow


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
        return self.db.query(AnnualReport).filter(AnnualReport.id == report_id).first()

    def get_by_client_year(self, client_id: int, tax_year: int) -> Optional[AnnualReport]:
        return (
            self.db.query(AnnualReport)
            .filter(AnnualReport.client_id == client_id, AnnualReport.tax_year == tax_year)
            .first()
        )

    def list_by_client(self, client_id: int) -> list[AnnualReport]:
        return (
            self.db.query(AnnualReport)
            .filter(AnnualReport.client_id == client_id)
            .order_by(AnnualReport.tax_year.desc())
            .all()
        )

    def list_by_status(
        self,
        status: AnnualReportStatus,
        tax_year: Optional[int] = None,
        assigned_to: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AnnualReport]:
        q = self.db.query(AnnualReport).filter(AnnualReport.status == status)
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
        q = self.db.query(AnnualReport).filter(AnnualReport.status == status)
        if tax_year:
            q = q.filter(AnnualReport.tax_year == tax_year)
        return q.count()

    def list_by_tax_year(
        self,
        tax_year: int,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AnnualReport]:
        q = (
            self.db.query(AnnualReport)
            .filter(AnnualReport.tax_year == tax_year)
            .order_by(AnnualReport.status.asc(), AnnualReport.filing_deadline.asc())
        )
        return self._paginate(q, page, page_size)

    def count_by_tax_year(self, tax_year: int) -> int:
        return self.db.query(AnnualReport).filter(AnnualReport.tax_year == tax_year).count()

    def list_all(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AnnualReport]:
        q = (
            self.db.query(AnnualReport)
            .order_by(AnnualReport.tax_year.desc(), AnnualReport.created_at.desc())
        )
        return self._paginate(q, page, page_size)

    def list_all_with_clients(self) -> list[tuple[AnnualReport, str]]:
        """Return all reports with client names (for Kanban view)."""
        return (
            self.db.query(AnnualReport, Client.full_name.label("client_name"))
            .join(Client, Client.id == AnnualReport.client_id)
            .order_by(AnnualReport.filing_deadline.asc().nulls_last(), AnnualReport.id.asc())
            .all()
        )

    def count_all(self) -> int:
        return self.db.query(AnnualReport).count()

    def list_overdue(self, tax_year: Optional[int] = None) -> list[AnnualReport]:
        """Reports past their filing deadline and not yet submitted."""
        now = utcnow()
        open_statuses = [
            AnnualReportStatus.NOT_STARTED,
            AnnualReportStatus.COLLECTING_DOCS,
            AnnualReportStatus.DOCS_COMPLETE,
            AnnualReportStatus.IN_PREPARATION,
            AnnualReportStatus.PENDING_CLIENT,
        ]
        q = (
            self.db.query(AnnualReport)
            .filter(
                AnnualReport.status.in_(open_statuses),
                AnnualReport.filing_deadline < now,
                AnnualReport.filing_deadline.isnot(None),
            )
        )
        if tax_year:
            q = q.filter(AnnualReport.tax_year == tax_year)
        return q.order_by(AnnualReport.filing_deadline.asc()).all()

    def update(self, report_id: int, **fields) -> Optional[AnnualReport]:
        report = self.get_by_id(report_id)
        return self._update_entity(report, touch_updated_at=True, **fields)

    # ── Season dashboard ───────────────────────────────────────────────────

    def get_season_summary(self, tax_year: int) -> dict:
        """
        Counts of each status for a given tax year (for dashboards).
        """
        all_reports = (
            self.db.query(AnnualReport)
            .filter(AnnualReport.tax_year == tax_year)
            .all()
        )
        summary = {s.value: 0 for s in AnnualReportStatus}
        for r in all_reports:
            summary[r.status.value] += 1
        summary["total"] = len(all_reports)
        return summary
