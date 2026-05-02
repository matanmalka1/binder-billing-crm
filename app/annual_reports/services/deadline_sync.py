"""Bridge: sync the ANNUAL_REPORT tax deadline when an annual report changes filing zone."""
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_enums import ANNUAL_REPORT_FILED_STATUSES, AnnualReportStatus
from app.annual_reports.models.annual_report_model import AnnualReport
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_query_repository import TaxDeadlineQueryRepository
from app.utils.time_utils import utcnow


def sync_annual_report_deadline(
    db: Session,
    report: AnnualReport,
    old_status: AnnualReportStatus,
    new_status: AnnualReportStatus,
    changed_by: Optional[int],
) -> None:
    """Complete or reopen the ANNUAL_REPORT tax deadline that matches this report."""
    entering_filed = new_status in ANNUAL_REPORT_FILED_STATUSES and old_status not in ANNUAL_REPORT_FILED_STATUSES
    leaving_filed = old_status in ANNUAL_REPORT_FILED_STATUSES and new_status not in ANNUAL_REPORT_FILED_STATUSES
    if not entering_filed and not leaving_filed:
        return

    client_record_id = ClientRecordRepository(db).get_by_id(report.client_record_id).id
    deadlines = TaxDeadlineQueryRepository(db).list_by_client_record(
        client_record_id=client_record_id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_from=date(report.tax_year + 1, 1, 1),
        due_to=date(report.tax_year + 2, 12, 31),
    )
    if not deadlines:
        return

    for deadline in deadlines:
        if entering_filed and deadline.status == TaxDeadlineStatus.PENDING:
            deadline.status = TaxDeadlineStatus.COMPLETED
            deadline.completed_at = utcnow()
            deadline.completed_by = changed_by
            db.flush()

        elif leaving_filed and deadline.status == TaxDeadlineStatus.COMPLETED:
            deadline.status = TaxDeadlineStatus.PENDING
            deadline.completed_at = None
            deadline.completed_by = None
            db.flush()
