"""Repository operations for annual report status history."""

from sqlalchemy.orm import Session

from app.annual_reports.models import AnnualReportStatus, AnnualReportStatusHistory
from app.utils.time import utcnow


class AnnualReportStatusHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def append_status_history(
        self,
        annual_report_id: int,
        from_status: AnnualReportStatus | None,
        to_status: AnnualReportStatus,
        changed_by: int,
        changed_by_name: str,
        note: str | None = None,
    ) -> AnnualReportStatusHistory:
        entry = AnnualReportStatusHistory(
            annual_report_id=annual_report_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            changed_by_name=changed_by_name,
            note=note,
            occurred_at=utcnow(),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_status_history(self, annual_report_id: int) -> list[AnnualReportStatusHistory]:
        return (
            self.db.query(AnnualReportStatusHistory)
            .filter(AnnualReportStatusHistory.annual_report_id == annual_report_id)
            .order_by(AnnualReportStatusHistory.occurred_at.asc())
            .all()
        )
