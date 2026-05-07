"""Read-only repository for grouped deadline aggregation queries."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline


class GroupedDeadlineRepository:
    def __init__(self, db: Session):
        self.db = db

    def fetch_for_grouping(
        self,
        *,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        client_name_ids: Optional[list[int]] = None,
    ) -> list[TaxDeadline]:
        """Fetch raw deadlines to be grouped in the service layer."""

        q = scope_to_active_clients(
            self.db.query(TaxDeadline), TaxDeadline
        ).filter(TaxDeadline.deleted_at.is_(None))

        if status:
            q = q.filter(TaxDeadline.status == status)
        if deadline_type:
            q = q.filter(TaxDeadline.deadline_type == deadline_type)
        if due_from is not None:
            q = q.filter(TaxDeadline.due_date >= due_from)
        if due_to is not None:
            q = q.filter(TaxDeadline.due_date <= due_to)
        if client_name_ids:
            q = q.filter(TaxDeadline.client_record_id.in_(client_name_ids))

        return q.order_by(TaxDeadline.due_date.asc()).all()

    def fetch_group_clients(
        self,
        *,
        deadline_type: DeadlineType,
        due_date: date,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TaxDeadline], int]:
        """Fetch per-client deadlines for a specific group, paginated."""
        q = scope_to_active_clients(
            self.db.query(TaxDeadline), TaxDeadline
        ).filter(
            TaxDeadline.deleted_at.is_(None),
            TaxDeadline.deadline_type == deadline_type,
            TaxDeadline.due_date == due_date,
        )

        if status:
            q = q.filter(TaxDeadline.status == status)

        total = q.count()
        items = q.order_by(TaxDeadline.client_record_id.asc()).offset(offset).limit(limit).all()
        return items, total
