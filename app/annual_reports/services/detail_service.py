from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.audit.constants import ACTION_ANNUAL_REPORT_DETAIL_UPDATED, ENTITY_ANNUAL_REPORT
from app.audit.services.entity_audit_writer import EntityAuditWriter
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

    def update_detail(self, report_id: int, actor_id: Optional[int] = None, **fields) -> AnnualReportDetail:
        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(ANNUAL_REPORT_NOT_FOUND.format(report_id=report_id), "ANNUAL_REPORT.NOT_FOUND")
        existing = self.repo.get_by_report_id(report_id)
        old_value = {key: getattr(existing, key, None) for key in fields} if fields else None
        detail = self.repo.update_meta(report_id, **fields)
        if fields:
            EntityAuditWriter(self.db).append(
                entity_type=ENTITY_ANNUAL_REPORT,
                entity_id=report_id,
                actor_id=actor_id,
                action=ACTION_ANNUAL_REPORT_DETAIL_UPDATED,
                old_value=old_value,
                new_value=fields,
            )
        return detail
