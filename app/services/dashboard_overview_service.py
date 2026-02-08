from datetime import date, timedelta

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models import Binder, BinderStatus, Client, ClientStatus


class DashboardOverviewService:
    """Sprint 2 dashboard overview business logic."""

    def __init__(self, db: Session):
        self.db = db

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
        
        week_end = reference_date + timedelta(days=7)
        
        # Total clients (all statuses)
        total_clients = self.db.query(func.count(Client.id)).scalar()
        
        # Active binders (status != RETURNED)
        active_binders = (
            self.db.query(func.count(Binder.id))
            .filter(Binder.status != BinderStatus.RETURNED)
            .scalar()
        )
        
        # Overdue binders (expected_return_at < today AND status != RETURNED)
        overdue_binders = (
            self.db.query(func.count(Binder.id))
            .filter(
                and_(
                    Binder.expected_return_at < reference_date,
                    Binder.status != BinderStatus.RETURNED,
                )
            )
            .scalar()
        )
        
        # Binders due today
        binders_due_today = (
            self.db.query(func.count(Binder.id))
            .filter(
                and_(
                    Binder.expected_return_at == reference_date,
                    Binder.status != BinderStatus.RETURNED,
                )
            )
            .scalar()
        )
        
        # Binders due this week (today + 7 days)
        binders_due_this_week = (
            self.db.query(func.count(Binder.id))
            .filter(
                and_(
                    Binder.expected_return_at >= reference_date,
                    Binder.expected_return_at <= week_end,
                    Binder.status != BinderStatus.RETURNED,
                )
            )
            .scalar()
        )
        
        return {
            "total_clients": total_clients or 0,
            "active_binders": active_binders or 0,
            "overdue_binders": overdue_binders or 0,
            "binders_due_today": binders_due_today or 0,
            "binders_due_this_week": binders_due_this_week or 0,
        }