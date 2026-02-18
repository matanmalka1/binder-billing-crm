from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models import AnnualReportDetail
from app.utils.time import utcnow


class AnnualReportDetailRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_report_id(self, report_id: int) -> Optional[AnnualReportDetail]:
        return (
            self.db.query(AnnualReportDetail)
            .filter(AnnualReportDetail.report_id == report_id)
            .first()
        )

    def upsert(self, report_id: int, **fields) -> AnnualReportDetail:
        detail = self.get_by_report_id(report_id)
        if detail is None:
            detail = AnnualReportDetail(report_id=report_id, **fields)
            self.db.add(detail)
        else:
            for key, value in fields.items():
                if hasattr(detail, key):
                    setattr(detail, key, value)
            detail.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(detail)
        return detail
