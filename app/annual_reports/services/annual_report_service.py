from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.annual_reports.repositories import AnnualReportRepository
from app.clients.repositories.client_repository import ClientRepository
from app.users.repositories.user_repository import UserRepository
from .create_service import AnnualReportCreateService
from .query_service import AnnualReportQueryService
from .season_service import AnnualReportSeasonService
from .schedule_service import AnnualReportScheduleService
from .status_service import AnnualReportStatusService
from .kanban_service import AnnualReportKanbanService
from .annex_service import AnnualReportAnnexService


class AnnualReportService(
    AnnualReportCreateService,
    AnnualReportStatusService,
    AnnualReportKanbanService,
    AnnualReportSeasonService,
    AnnualReportScheduleService,
    AnnualReportQueryService,
    AnnualReportAnnexService,
):
    """Facade combining annual report operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnnualReportRepository(db)
        # Cross-domain repositories are wired only at facade level (service boundary).
        # Lower annual_reports service mixins must consume self.client_repo/self.user_repo only.
        self.client_repo = ClientRepository(db)
        self.user_repo = UserRepository(db)

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
