"""Bridge: sync the ANNUAL_REPORT tax deadline when an annual report changes filing zone."""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_enums import ANNUAL_REPORT_FILED_STATUSES, AnnualReportStatus
from app.annual_reports.models.annual_report_model import AnnualReport
from app.annual_reports.services.constants import ANNUAL_DEADLINE_REMINDER_DAYS_BEFORE
from app.annual_reports.services.messages import ANNUAL_DEADLINE_REMINDER_MESSAGE
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_query_repository import TaxDeadlineQueryRepository
from app.reminders.models.reminder import ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
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
        due_to=date(report.tax_year + 1, 12, 31),
    )
    if not deadlines:
        return

    reminder_repo = ReminderRepository(db)

    for deadline in deadlines:
        if entering_filed and deadline.status == TaxDeadlineStatus.PENDING:
            deadline.status = TaxDeadlineStatus.COMPLETED
            deadline.completed_at = utcnow()
            deadline.completed_by = changed_by
            db.flush()
            reminder_repo.cancel_pending_by_tax_deadline_flush(deadline.id)

        elif leaving_filed and deadline.status == TaxDeadlineStatus.COMPLETED:
            deadline.status = TaxDeadlineStatus.PENDING
            deadline.completed_at = None
            deadline.completed_by = None
            db.flush()
            if not reminder_repo.exists_pending_for_tax_deadline(deadline.id):
                send_on = deadline.due_date - timedelta(days=ANNUAL_DEADLINE_REMINDER_DAYS_BEFORE)
                reminder_repo.create_flush(
                    reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
                    target_date=deadline.due_date,
                    days_before=ANNUAL_DEADLINE_REMINDER_DAYS_BEFORE,
                    send_on=send_on,
                    message=ANNUAL_DEADLINE_REMINDER_MESSAGE.format(
                        days_before=ANNUAL_DEADLINE_REMINDER_DAYS_BEFORE,
                        due_date=deadline.due_date,
                    ),
                    client_record_id=client_record_id,
                    tax_deadline_id=deadline.id,
                    created_by=changed_by,
                )
