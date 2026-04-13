from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.annual_reports.models.annual_report_detail import AnnualReportDetail
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.annual_reports.repositories.detail_repository import AnnualReportDetailRepository
from app.annual_reports.services.messages import ANNUAL_REPORT_NOT_FOUND


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
            raise NotFoundError(ANNUAL_REPORT_NOT_FOUND.format(report_id=report_id), "ANNUAL_REPORT.NOT_FOUND")
        return self.repo.update_meta(report_id, **fields)
