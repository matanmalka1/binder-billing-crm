from datetime import date
from sqlalchemy.orm import Session

from app.repositories.dashboard_overview_repository import DashboardOverviewRepository


class DashboardOverviewService:
    """Sprint 2 dashboard overview business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = DashboardOverviewRepository(db)

    def get_overview(self, reference_date: date = None) -> dict:
        """
        Get dashboard overview metrics.
        
        Returns:
            {
                "total_clients": int,
                "active_binders": int,
                "overdue_binders": int,
                "binders_due_today": int,
                "binders_due_this_week": int
            }
        """
        if reference_date is None:
            reference_date = date.today()
        return self.repo.get_overview_metrics(reference_date)
