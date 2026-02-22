from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client import Client


class DashboardOverviewRepository:
    """Data access layer for dashboard overview metrics."""

    def __init__(self, db: Session):
        self.db = db

    def get_overview_metrics(self, reference_date: date) -> dict:
        """Compute dashboard overview metrics from ORM queries."""
        total_clients = self.db.query(func.count(Client.id)).scalar() or 0

        active_binders = (
            self.db.query(func.count(Binder.id))
            .filter(Binder.status != BinderStatus.RETURNED)
            .scalar()
            or 0
        )

        return {
            "total_clients": total_clients,
            "active_binders": active_binders,
        }
