from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.guards.client_record_guards import assert_client_record_is_active
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.constants import FAR_FUTURE_DATE
from app.tax_deadline.services.due_dates import resolve_due_date
from app.utils.time_utils import utcnow
from app.reminders.services.reminder_service import ReminderService
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.annual_reports.models.annual_report_enums import ANNUAL_REPORT_FILED_STATUSES


class TaxDeadlineService:
    """Tax deadline CRUD business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)

    def create_deadline(
        self,
        client_record_id: int,
        deadline_type: DeadlineType,
        due_date: Optional[date] = None,
        period: Optional[str] = None,
        tax_year: Optional[int] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        """Create new tax deadline."""
        client_record = ClientRecordRepository(self.db).get_by_id(client_record_id)
        if not client_record:
            raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT_RECORD.NOT_FOUND")
        assert_client_record_is_active(client_record)
        client_record_id = int(client_record.id)
        due_date = resolve_due_date(self.db, client_record, deadline_type, due_date, period)

        if deadline_type == DeadlineType.ANNUAL_REPORT:
            tax_year = tax_year or due_date.year - 1
            report = AnnualReportRepository(self.db).get_by_client_record_year(client_record_id, tax_year)
            if report and report.status in ANNUAL_REPORT_FILED_STATUSES:
                raise AppError(
                    f"דוח שנתי לשנת {tax_year} כבר הוגש — לא ניתן ליצור מועד הגשה חדש",
                    "TAX_DEADLINE.ANNUAL_REPORT_ALREADY_FILED",
                )
        else:
            tax_year = None

        deadline = self.deadline_repo.create(
            client_record_id=client_record_id,
            deadline_type=deadline_type,
            due_date=due_date,
            period=period,
            tax_year=tax_year,
            payment_amount=payment_amount,
            description=description,
        )

        ReminderService(self.db).create_tax_deadline_reminder(
            client_record_id=client_record_id,
            tax_deadline_id=deadline.id,
            target_date=due_date,
            days_before=7,
        )

        return deadline

    def mark_completed(self, deadline_id: int, completed_by: Optional[int] = None) -> TaxDeadline:
        """Mark deadline as completed."""
        deadline = self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

        if deadline.status == TaxDeadlineStatus.COMPLETED:
            return deadline

        return self.deadline_repo.update_status(
            deadline_id,
            TaxDeadlineStatus.COMPLETED,
            completed_at=utcnow(),
            completed_by=completed_by,
        )

    def reopen_deadline(self, deadline_id: int) -> TaxDeadline:
        """Revert a completed deadline back to pending."""
        deadline = self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

        if deadline.status == TaxDeadlineStatus.PENDING:
            return deadline

        return self.deadline_repo.update_status(
            deadline_id,
            TaxDeadlineStatus.PENDING,
            completed_at=None,
            completed_by=None,
        )

    def update_deadline(
        self,
        deadline_id: int,
        *,
        deadline_type: Optional[DeadlineType] = None,
        due_date: Optional[date] = None,
        period: Optional[str] = None,
        tax_year: Optional[int] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        """Update editable fields on a deadline."""
        if not any([
            deadline_type,
            due_date,
            period is not None,
            tax_year is not None,
            payment_amount is not None,
            description is not None,
        ]):
            raise AppError("לא סופקו שדות לעדכון", "TAX_DEADLINE.NO_FIELDS_PROVIDED")

        existing = self.deadline_repo.get_by_id(deadline_id)
        if not existing:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

        next_type = deadline_type or existing.deadline_type
        next_period = period if period is not None else existing.period
        should_recompute_due_date = (
            deadline_type is not None or due_date is not None or period is not None
        )
        if next_type == DeadlineType.VAT and should_recompute_due_date:
            client_record = ClientRecordRepository(self.db).get_by_id(existing.client_record_id)
            due_date = resolve_due_date(self.db, client_record, next_type, due_date, next_period)

        deadline = self.deadline_repo.update(
            deadline_id,
            deadline_type=deadline_type,
            due_date=due_date,
            period=period,
            tax_year=tax_year,
            payment_amount=payment_amount,
            description=description,
        )

        if due_date:
            reminder_service = ReminderService(self.db)
            reminder_service.cancel_reminders_for_tax_deadline(deadline_id)
            reminder_service.create_tax_deadline_reminder(
                client_record_id=deadline.client_record_id,
                tax_deadline_id=deadline.id,
                target_date=deadline.due_date,
                days_before=7,
            )

        return deadline

    def get_deadline(self, deadline_id: int) -> TaxDeadline:
        """Return deadline by ID. Raises NotFoundError if not found."""
        deadline = self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")
        return deadline

    def list_all_pending(self) -> list[TaxDeadline]:
        """Return all pending deadlines regardless of client."""
        return self.deadline_repo.list_pending_due_by_date(date.today(), FAR_FUTURE_DATE)

    def delete_deadline(self, deadline_id: int, deleted_by: int) -> None:
        """Soft-delete a deadline."""
        deleted = self.deadline_repo.delete(deadline_id, deleted_by=deleted_by)
        if not deleted:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

    def get_client_deadlines(
        self,
        client_record_id: int,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """Get deadlines for a specific client."""
        client_record_id = int(ClientRecordRepository(self.db).get_by_id(client_record_id).id)
        return self.deadline_repo.list_by_client_record(client_record_id, status, deadline_type)
