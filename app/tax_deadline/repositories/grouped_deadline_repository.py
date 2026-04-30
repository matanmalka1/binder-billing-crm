"""Read-only repository for grouped deadline aggregation queries."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus


_MAX_GROUPS = 200
_DEFAULT_WINDOW_DAYS = 90


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
        """Fetch raw deadlines to be grouped in the service layer.

        Applies a default 90-day window when no date range given.
        Hard cap: returns at most _MAX_GROUPS * N rows; service enforces group cap.
        """
        today = date.today()
        effective_from = due_from if due_from is not None else today
        effective_to = due_to if due_to is not None else date(
            today.year + (1 if today.month + 3 > 12 else 0),
            ((today.month + 3 - 1) % 12) + 1,
            today.day,
        )

        q = scope_to_active_clients(
            self.db.query(TaxDeadline), TaxDeadline
        ).filter(TaxDeadline.deleted_at.is_(None))

        if status:
            q = q.filter(TaxDeadline.status == status)
        if deadline_type:
            q = q.filter(TaxDeadline.deadline_type == deadline_type)
        if due_from is not None or due_to is not None:
            q = q.filter(TaxDeadline.due_date >= effective_from)
            q = q.filter(TaxDeadline.due_date <= effective_to)
        else:
            q = q.filter(TaxDeadline.due_date >= effective_from)
            q = q.filter(TaxDeadline.due_date <= effective_to)
        if client_name_ids:
            q = q.filter(TaxDeadline.client_record_id.in_(client_name_ids))

        return q.order_by(TaxDeadline.due_date.asc()).all()

    def fetch_group_clients(
        self,
        *,
        deadline_type: DeadlineType,
        due_date: date,
        period: Optional[str],
        tax_year: Optional[int],
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

        if period is not None:
            q = q.filter(TaxDeadline.period == period)
        elif tax_year is not None:
            q = q.filter(TaxDeadline.tax_year == tax_year)

        if status:
            q = q.filter(TaxDeadline.status == status)

        total = q.count()
        items = q.order_by(TaxDeadline.client_record_id.asc()).offset(offset).limit(limit).all()
        return items, total
