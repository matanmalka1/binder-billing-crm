"""Bridge: sync the ANNUAL_REPORT tax deadline when an annual report changes filing zone."""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_enums import ANNUAL_REPORT_FILED_STATUSES, AnnualReportStatus
from app.annual_reports.models.annual_report_model import AnnualReport
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_query_repository import TaxDeadlineQueryRepository
from app.reminders.models.reminder import ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time_utils import utcnow

_REMINDER_DAYS_BEFORE = 7


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

    deadlines = TaxDeadlineQueryRepository(db).list_by_client(
        client_id=report.client_id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_from=date(report.tax_year + 1, 1, 1),
        due_to=date(report.tax_year + 1, 12, 31),
    )
    if not deadlines:
        return

    reminder_repo = ReminderRepository(db)
    dirty = False

    for deadline in deadlines:
        if entering_filed and deadline.status == TaxDeadlineStatus.PENDING:
            deadline.status = TaxDeadlineStatus.COMPLETED
            deadline.completed_at = utcnow()
            deadline.completed_by = changed_by
            db.flush()
            reminder_repo.cancel_pending_by_tax_deadline_flush(deadline.id)
            dirty = True

        elif leaving_filed and deadline.status == TaxDeadlineStatus.COMPLETED:
            deadline.status = TaxDeadlineStatus.PENDING
            deadline.completed_at = None
            deadline.completed_by = None
            db.flush()
            if not reminder_repo.exists_pending_for_tax_deadline(deadline.id):
                send_on = deadline.due_date - timedelta(days=_REMINDER_DAYS_BEFORE)
                reminder_repo.create_flush(
                    reminder_type=ReminderType.TAX_DEADLINE_APPROACHING,
                    target_date=deadline.due_date,
                    days_before=_REMINDER_DAYS_BEFORE,
                    send_on=send_on,
                    message=f"תזכורת: מועד מס בעוד {_REMINDER_DAYS_BEFORE} ימים ({deadline.due_date})",
                    client_id=deadline.client_id,
                    tax_deadline_id=deadline.id,
                    created_by=changed_by,
                )
            dirty = True

    if dirty:
        # explicit commit: this service owns the batch sync transaction boundary
        db.commit()
