from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus, UrgencyLevel
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_lookup import assert_client_allows_create, get_client_or_raise
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.utils.time_utils import utcnow
from app.reminders.services.reminder_service import ReminderService


class TaxDeadlineService:
    """Tax deadline management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.client_repo = ClientRepository(db)

    def create_deadline(
        self,
        client_id: int,
        deadline_type: DeadlineType,
        due_date: date,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        """Create new tax deadline."""
        client = get_client_or_raise(self.db, client_id)
        assert_client_allows_create(client)

        deadline = self.deadline_repo.create(
            client_id=client_id,
            deadline_type=deadline_type,
            due_date=due_date,
            payment_amount=payment_amount,
            description=description,
        )

        ReminderService(self.db).create_tax_deadline_reminder(
            client_id=client_id,
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

    def get_client_deadlines(
        self,
        client_id: int,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """Get deadlines for client."""
        return self.deadline_repo.list_by_client(client_id, status, deadline_type)

    def get_deadlines_by_client_name(
        self,
        client_name: str,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """Get deadlines filtered by client name substring."""
        clients, _ = self.client_repo.search(client_name=client_name, page=1, page_size=500)
        if not clients:
            return []
        client_ids = [c.id for c in clients]
        return self.deadline_repo.list_by_client_ids(client_ids, status, deadline_type)

    def get_timeline(self, client_id: int) -> list:
        """Return deadlines for a client sorted by due_date asc with days_remaining and milestone_label."""
        from app.tax_deadline.services.timeline_service import build_timeline
        return build_timeline(client_id, self.client_repo, self.deadline_repo)

    def build_client_name_map(self, deadlines: list[TaxDeadline]) -> dict[int, str]:
        """Return {client_id: full_name} for the given deadlines."""
        client_ids = list({d.client_id for d in deadlines})
        clients = self.client_repo.list_by_ids(client_ids) if client_ids else []
        return {c.id: c.full_name for c in clients}

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
