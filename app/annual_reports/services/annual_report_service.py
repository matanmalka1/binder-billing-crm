from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.annual_reports.repositories.annex_data_repository import AnnexDataRepository
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.users.repositories.user_repository import UserRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
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
        self.annex_repo = AnnexDataRepository(db)
        # Cross-domain repositories are wired only at facade level (service boundary).
        # Lower annual_reports service mixins must consume these via self.<repo_name> only.
        self.business_repo = BusinessRepository(db)
        self.user_repo = UserRepository(db)
        self.vat_repo = VatWorkItemRepository(db)
        self.advance_repo = AdvancePaymentRepository(db)

    def assert_report_exists(self, report_id: int) -> None:
        """Raise NotFoundError if the report does not exist."""
        if not self.repo.get_by_id(report_id):
            raise NotFoundError(f"דוח שנתי {report_id} לא נמצא", "ANNUAL_REPORT.NOT_FOUND")

    def delete_report(self, report_id: int, actor_id: int, actor_name: str) -> bool:
        """Soft-delete an annual report. Returns False if not found."""
        report = self.repo.get_by_id(report_id)
        if not report:
            return False
        self._cancel_pending_signature_requests(report_id, actor_id, actor_name, "דוח נמחק")
        return self.repo.soft_delete(report_id, deleted_by=actor_id)


__all__ = ["AnnualReportService"]
