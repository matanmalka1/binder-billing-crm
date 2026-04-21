from sqlalchemy.orm import Session

from app.annual_reports.repositories.report_repository import AnnualReportReportRepository


class AnnualReportClientStatusService:
    def __init__(self, db: Session):
        self.repo = AnnualReportReportRepository(db)

    def cancel_open_by_client_record(self, client_record_id: int) -> int:
        return self.repo.cancel_open_by_client_record(client_record_id)
