from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import DeadlineType, TaxDeadline, UrgencyLevel
from app.repositories.client_repository import ClientRepository
from app.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.utils.time import utcnow


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
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        return self.deadline_repo.create(
            client_id=client_id,
            deadline_type=deadline_type,
            due_date=due_date,
            payment_amount=payment_amount,
            description=description,
        )

    def mark_completed(self, deadline_id: int) -> TaxDeadline:
        """Mark deadline as completed."""
        deadline = self.deadline_repo.get_by_id(deadline_id)
        if not deadline:
            raise ValueError(f"Deadline {deadline_id} not found")

        if deadline.status == "completed":
            return deadline

        return self.deadline_repo.update_status(
            deadline_id,
            "completed",
            completed_at=utcnow(),
        )

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
        if deadline.status == "completed":
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