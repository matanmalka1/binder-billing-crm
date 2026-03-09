from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.annual_reports.repositories import AnnualReportRepository
from app.clients.repositories.client_repository import ClientRepository
from .create_service import AnnualReportCreateService
from .query_service import AnnualReportQueryService
from .schedule_service import AnnualReportScheduleService
from .status_service import AnnualReportStatusService
from .annex_service import AnnualReportAnnexService


class AnnualReportService(
    AnnualReportCreateService,
    AnnualReportStatusService,
    AnnualReportScheduleService,
    AnnualReportQueryService,
    AnnualReportAnnexService,
):
    """Facade combining annual report operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnnualReportRepository(db)
        self.client_repo = ClientRepository(db)

    def assert_report_exists(self, report_id: int) -> None:
        """Raise NotFoundError if the report does not exist."""
        if not self.repo.get_by_id(report_id):
            raise NotFoundError("Annual report not found", "ANNUAL_REPORT.NOT_FOUND")

    def delete_report(self, report_id: int, actor_id: int) -> bool:
        """Soft-delete an annual report. Returns False if not found."""
        report = self.repo.get_by_id(report_id)
        if not report:
            return False
        return self.repo.soft_delete(report_id, deleted_by=actor_id)


__all__ = ["AnnualReportService"]
