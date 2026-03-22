from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.businesses.services.business_guards import assert_business_allows_create
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.constants import FAR_FUTURE_DATE
from app.utils.time_utils import utcnow
from app.reminders.services.reminder_service import ReminderService


class TaxDeadlineService:
    """Tax deadline CRUD business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.business_repo = BusinessRepository(db)

    def create_deadline(
        self,
        business_id: int,
        deadline_type: DeadlineType,
        due_date: date,
        period: Optional[str] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        """Create new tax deadline."""
        business = get_business_or_raise(self.db, business_id)
        assert_business_allows_create(business)

        deadline = self.deadline_repo.create(
            business_id=business_id,
            deadline_type=deadline_type,
            due_date=due_date,
            period=period,
            payment_amount=payment_amount,
            description=description,
        )

        ReminderService(self.db).create_tax_deadline_reminder(
            business_id=business_id,
            tax_deadline_id=deadline.id,
            target_date=due_date,
            days_before=7,
        )

        return deadline

    def mark_completed(self, deadline_id: int) -> TaxDeadline:
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
        )

    def update_deadline(
        self,
        deadline_id: int,
        *,
        deadline_type: Optional[DeadlineType] = None,
        due_date: Optional[date] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        """Update editable fields on a deadline."""
        if not any([deadline_type, due_date, payment_amount is not None, description is not None]):
            raise AppError("לא סופקו שדות לעדכון", "TAX_DEADLINE.NO_FIELDS_PROVIDED")

        deadline = self.deadline_repo.update(
            deadline_id,
            deadline_type=deadline_type,
            due_date=due_date,
            payment_amount=payment_amount,
            description=description,
        )

        if not deadline:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

        return deadline

    def get_deadline(self, deadline_id: int) -> TaxDeadline:
        """Return deadline by ID. Raises NotFoundError if not found."""
        deadline = self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")
        return deadline

    def list_all_pending(self) -> list[TaxDeadline]:
        """Return all pending deadlines regardless of business."""
        return self.deadline_repo.list_pending_due_by_date(date.today(), FAR_FUTURE_DATE)

    def delete_deadline(self, deadline_id: int, deleted_by: int) -> None:
        """Soft-delete a deadline."""
        deleted = self.deadline_repo.delete(deadline_id, deleted_by=deleted_by)
        if not deleted:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

    def get_business_deadlines(
        self,
        business_id: int,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """Get deadlines for a specific business."""
        return self.deadline_repo.list_by_business(business_id, status, deadline_type)
