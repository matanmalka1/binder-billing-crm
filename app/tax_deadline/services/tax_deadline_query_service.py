from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus, UrgencyLevel
from app.businesses.repositories.business_repository import BusinessRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.constants import (
    FAR_FUTURE_DATE,
    URGENCY_RED_DAYS,
    URGENCY_YELLOW_DAYS,
)


class TaxDeadlineQueryService:
    """Read-only query methods for tax deadlines."""

    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.business_repo = BusinessRepository(db)

    def list_all_pending(self) -> list[TaxDeadline]:
        """Return all pending deadlines regardless of business."""
        return self.deadline_repo.list_pending_due_by_date(date.today(), FAR_FUTURE_DATE)

    def get_upcoming_deadlines(
        self,
        days_ahead: int = 7,
        reference_date: Optional[date] = None,
    ) -> list[TaxDeadline]:
        """Get pending deadlines within the next N days."""
        if reference_date is None:
            reference_date = date.today()
        to_date = reference_date + timedelta(days=days_ahead)
        return self.deadline_repo.list_pending_due_by_date(reference_date, to_date)

    def get_overdue_deadlines(
        self,
        reference_date: Optional[date] = None,
    ) -> list[TaxDeadline]:
        """Get all overdue pending deadlines."""
        if reference_date is None:
            reference_date = date.today()
        return self.deadline_repo.list_overdue(reference_date)

    def compute_urgency(
        self,
        deadline: TaxDeadline,
        reference_date: Optional[date] = None,
    ) -> Optional[UrgencyLevel]:
        """Compute urgency level for a deadline."""
        if deadline.status == TaxDeadlineStatus.COMPLETED:
            return None
        if reference_date is None:
            reference_date = date.today()

        days_remaining = (deadline.due_date - reference_date).days

        if days_remaining < 0:
            return UrgencyLevel.OVERDUE
        elif days_remaining <= URGENCY_RED_DAYS:
            return UrgencyLevel.RED
        elif days_remaining <= URGENCY_YELLOW_DAYS:
            return UrgencyLevel.YELLOW
        else:
            return UrgencyLevel.GREEN

    def get_deadlines_by_client_name(
        self,
        client_name: str,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """Get deadlines filtered by business name substring."""
        businesses = self.business_repo.list(search=client_name, page=1, page_size=500)
        if not businesses:
            return []
        business_ids = [b.id for b in businesses]
        return self.deadline_repo.list_by_business_ids(business_ids, status, deadline_type)

    def get_timeline(self, business_id: int) -> list:
        """Return deadlines for a business sorted by due_date asc with days_remaining and milestone_label."""
        from app.tax_deadline.services.timeline_service import build_timeline
        return build_timeline(business_id, self.business_repo, self.deadline_repo)

    def build_business_name_map(self, deadlines: list[TaxDeadline]) -> dict[int, str]:
        """Return {business_id: business_name} for the given deadlines."""
        business_ids = list({d.business_id for d in deadlines})
        businesses = self.business_repo.list_by_ids(business_ids) if business_ids else []
        return {b.id: b.full_name for b in businesses}

    def build_client_id_map(self, deadlines: list[TaxDeadline]) -> dict[int, int]:
        """Return {business_id: client_id} for the given deadlines."""
        business_ids = list({d.business_id for d in deadlines})
        businesses = self.business_repo.list_by_ids(business_ids) if business_ids else []
        return {b.id: b.client_id for b in businesses}

    def get_urgent_deadlines_summary(
        self,
        reference_date: Optional[date] = None,
    ) -> dict:
        """Get summary of urgent and upcoming deadlines for the dashboard."""
        if reference_date is None:
            reference_date = date.today()

        upcoming = self.get_upcoming_deadlines(URGENCY_YELLOW_DAYS, reference_date)
        overdue = self.get_overdue_deadlines(reference_date)

        urgent = []
        for deadline in overdue:
            urgent.append({
                "deadline": deadline,
                "urgency": UrgencyLevel.OVERDUE,
                "days_remaining": (deadline.due_date - reference_date).days,
            })

        for deadline in upcoming:
            urgency = self.compute_urgency(deadline, reference_date)
            if urgency in (UrgencyLevel.RED, UrgencyLevel.YELLOW):
                urgent.append({
                    "deadline": deadline,
                    "urgency": urgency,
                    "days_remaining": (deadline.due_date - reference_date).days,
                })

        return {"urgent": urgent, "upcoming": upcoming}
