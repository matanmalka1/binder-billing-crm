from sqlalchemy.orm import Session

from app.annual_reports.repositories import AnnualReportRepository
from app.clients.repositories.client_repository import ClientRepository
from .create_service import AnnualReportCreateService
from .query_service import AnnualReportQueryService
from .schedule_service import AnnualReportScheduleService
from .status_service import AnnualReportStatusService


class AnnualReportService(
    AnnualReportCreateService,
    AnnualReportStatusService,
    AnnualReportScheduleService,
    AnnualReportQueryService,
):
    """Facade combining annual report operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnnualReportRepository(db)
        self.client_repo = ClientRepository(db)


__all__ = ["AnnualReportService"]
