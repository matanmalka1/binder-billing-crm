from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models import AnnualReportDetail
from app.annual_reports.repositories import AnnualReportDetailRepository
from app.annual_reports.repositories import AnnualReportRepository


class AnnualReportDetailService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AnnualReportDetailRepository(db)
        self.report_repo = AnnualReportRepository(db)

    def get_detail(self, report_id: int) -> Optional[AnnualReportDetail]:
        return self.repo.get_by_report_id(report_id)

    def update_detail(self, report_id: int, **fields) -> AnnualReportDetail:
        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValueError(f"Annual report {report_id} not found")
        return self.repo.upsert(report_id, **fields)
