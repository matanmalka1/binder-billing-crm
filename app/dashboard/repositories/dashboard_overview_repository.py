from datetime import date, timedelta

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client import Client
from app.binders.services.sla_service import SLAService


class DashboardOverviewRepository:
    """Data access layer for dashboard overview metrics (Sprint 2)."""

    def __init__(self, db: Session):
        self.db = db

    def get_overview_metrics(self, reference_date: date) -> dict:
        """Compute dashboard overview metrics from ORM queries."""
        week_end = reference_date + timedelta(days=7)

        total_clients = self.db.query(func.count(Client.id)).scalar() or 0

        active_binders = (
            self.db.query(func.count(Binder.id))
            .filter(Binder.status != BinderStatus.RETURNED)
            .scalar()
            or 0
        )

        overdue_binders = (
            self.db.query(func.count(Binder.id))
            .filter(SLAService.overdue_filter(reference_date))
            .scalar()
            or 0
        )

        binders_due_today = (
            self.db.query(func.count(Binder.id))
            .filter(SLAService.due_today_filter(reference_date))
            .scalar()
            or 0
        )

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
            or 0
        )

        return {
            "total_clients": total_clients,
            "active_binders": active_binders,
            "overdue_binders": overdue_binders,
            "binders_due_today": binders_due_today,
            "binders_due_this_week": binders_due_this_week,
        }
