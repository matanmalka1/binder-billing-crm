"""Public AnnualReportRepository facade composed of per-domain repositories."""

from sqlalchemy.orm import Session

from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
from app.annual_reports.repositories.schedule_repository import AnnualReportScheduleRepository
from app.annual_reports.repositories.status_history_repository import AnnualReportStatusHistoryRepository


class AnnualReportRepository(
    AnnualReportReportRepository,
    AnnualReportScheduleRepository,
    AnnualReportStatusHistoryRepository,
):
    def __init__(self, db: Session):
        # Each mixin expects self.db
        self.db = db


__all__ = ["AnnualReportRepository"]
