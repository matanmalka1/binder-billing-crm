from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus, UrgencyLevel
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.businesses.services.business_guards import assert_business_allows_create
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.utils.time_utils import utcnow
from app.reminders.services.reminder_service import ReminderService


class TaxDeadlineService:
    """Tax deadline management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.business_repo = BusinessRepository(db)

    def create_deadline(
        self,
        business_id: int,
        deadline_type: DeadlineType,
        due_date: date,
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
            raise NotFoundError(f"המועד האחרון {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

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
            raise NotFoundError(f"המועד האחרון {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

        return deadline

    def get_deadline(self, deadline_id: int) -> TaxDeadline:
        """Return deadline by ID. Raises NotFoundError if not found."""
        deadline = self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            raise NotFoundError(f"מועד המס {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")
        return deadline

    def list_all_pending(self) -> list[TaxDeadline]:
        """Return all pending deadlines regardless of client."""
        return self.deadline_repo.list_pending_due_by_date(
            date.today(), date(2099, 12, 31)
        )

    def delete_deadline(self, deadline_id: int) -> None:
        """Delete a deadline."""
        deleted = self.deadline_repo.delete(deadline_id)
        if not deleted:
            raise NotFoundError(f"המועד האחרון {deadline_id} לא נמצא", "TAX_DEADLINE.NOT_FOUND")

    def get_upcoming_deadlines(
        self,
        days_ahead: int = 7,
        reference_date: Optional[date] = None,
    ) -> list[TaxDeadline]:
        """Get pending deadlines within specified days."""
        if reference_date is None:
            reference_date = date.today()

        to_date = reference_date + timedelta(days=days_ahead)

        return self.deadline_repo.list_pending_due_by_date(reference_date, to_date)

    def get_overdue_deadlines(
        self,
        reference_date: Optional[date] = None,
    ) -> list[TaxDeadline]:
        """Get all overdue deadlines."""
        if reference_date is None:
            reference_date = date.today()

        return self.deadline_repo.list_overdue(reference_date)

    def compute_urgency(
        self,
        deadline: TaxDeadline,
        reference_date: Optional[date] = None,
    ) -> Optional[UrgencyLevel]:
        """Compute urgency level for deadline."""
        if deadline.status == TaxDeadlineStatus.COMPLETED:
            return None

        if reference_date is None:
            reference_date = date.today()

        days_remaining = (deadline.due_date - reference_date).days

        if days_remaining < 0:
            return UrgencyLevel.OVERDUE
        elif days_remaining <= 2:
            return UrgencyLevel.RED
        elif days_remaining <= 7:
            return UrgencyLevel.YELLOW
        else:
            return UrgencyLevel.GREEN

    def get_business_deadlines(
        self,
        business_id: int,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """Get deadlines for client."""
        return self.deadline_repo.list_by_business(business_id, status, deadline_type)

    def get_deadlines_by_client_name(
        self,
        client_name: str,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """Get deadlines filtered by client name substring."""
        businesses, _ = self.business_repo.search(business_name=client_name, page=1, page_size=500)
        if not businesses:
            return []
        business_ids = [b.id for b in businesses]
        return self.deadline_repo.list_by_business_ids(business_ids, status, deadline_type)

    def get_timeline(self, business_id: int) -> list:
        """Return deadlines for a client sorted by due_date asc with days_remaining and milestone_label."""
        from app.tax_deadline.services.timeline_service import build_timeline
        return build_timeline(business_id, self.business_repo, self.deadline_repo)

    def build_business_name_map(self, deadlines: list[TaxDeadline]) -> dict[int, str]:
        """Return {business_id: business_name} for the given deadlines."""
        business_ids = list({d.business_id for d in deadlines})
        businesses = self.business_repo.list_by_ids(business_ids) if business_ids else []
        return {b.id: b.business_name for b in businesses}

    def get_urgent_deadlines_summary(
        self,
        reference_date: Optional[date] = None,
    ) -> dict:
        """Get summary of urgent deadlines for dashboard."""
        if reference_date is None:
            reference_date = date.today()

        upcoming = self.get_upcoming_deadlines(7, reference_date)
        overdue = self.get_overdue_deadlines(reference_date)

        urgent = []
        for deadline in overdue:
            urgent.append(
                {
                    "deadline": deadline,
                    "urgency": UrgencyLevel.OVERDUE,
                    "days_remaining": (deadline.due_date - reference_date).days,
                }
            )

        for deadline in upcoming:
            urgency = self.compute_urgency(deadline, reference_date)
            if urgency in (UrgencyLevel.RED, UrgencyLevel.YELLOW):
                urgent.append(
                    {
                        "deadline": deadline,
                        "urgency": urgency,
                        "days_remaining": (deadline.due_date - reference_date).days,
                    }
                )

        return {"urgent": urgent, "upcoming": upcoming}
