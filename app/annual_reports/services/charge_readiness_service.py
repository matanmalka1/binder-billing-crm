"""Service for listing charges linked to an annual report.

Charges are informational only — they do not block report submission.
"""

from sqlalchemy.orm import Session

from app.charge.repositories.charge_annual_report_repository import ChargeAnnualReportRepository
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
from app.core.exceptions import NotFoundError
from app.annual_reports.services.messages import ANNUAL_REPORT_NOT_FOUND


class ChargeReadinessService:
    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeAnnualReportRepository(db)
        self.report_repo = AnnualReportReportRepository(db)

    def _get_report_or_raise(self, report_id: int):
        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(ANNUAL_REPORT_NOT_FOUND.format(report_id=report_id), "ANNUAL_REPORT.NOT_FOUND")
        return report

    def list_charges(
        self, report_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list, int]:
        """Return paginated charges linked to this annual report."""
        self._get_report_or_raise(report_id)
        return self.charge_repo.list_by_annual_report(report_id, page=page, page_size=page_size)
