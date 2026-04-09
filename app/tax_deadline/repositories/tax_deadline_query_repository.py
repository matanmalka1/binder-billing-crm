"""Read-only queries for TaxDeadline entities."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus


class TaxDeadlineQueryRepository:
    def __init__(self, db: Session):
        self.db = db

    def _base_query(self):
        return self.db.query(TaxDeadline).filter(TaxDeadline.deleted_at.is_(None))

    def get_by_id(self, deadline_id: int) -> Optional[TaxDeadline]:
        """Retrieve a non-deleted deadline by ID."""
        return (
            self.db.query(TaxDeadline)
            .filter(TaxDeadline.id == deadline_id, TaxDeadline.deleted_at.is_(None))
            .first()
        )

    def list_pending_due_by_date(
        self,
        from_date: date,
        to_date: date,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[TaxDeadline]:
        """List pending, non-deleted deadlines due within [from_date, to_date].

        Use limit/offset for SQL-level pagination (preferred over Python-slicing).
        """
        q = (
            self.db.query(TaxDeadline)
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.status == TaxDeadlineStatus.PENDING,
                TaxDeadline.due_date >= from_date,
                TaxDeadline.due_date <= to_date,
            )
            .order_by(TaxDeadline.due_date.asc())
        )
        if offset:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def count_pending_due_by_date(self, from_date: date, to_date: date) -> int:
        """Return the true count of pending deadlines in [from_date, to_date]."""
        return (
            self.db.query(TaxDeadline)
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.status == TaxDeadlineStatus.PENDING,
                TaxDeadline.due_date >= from_date,
                TaxDeadline.due_date <= to_date,
            )
            .count()
        )

    def list_filtered(
        self,
        *,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        period: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[TaxDeadline]:
        """List non-deleted deadlines with optional status/type/date/period filters."""
        query = self._base_query()
        if status:
            query = query.filter(TaxDeadline.status == status)
        if deadline_type:
            query = query.filter(TaxDeadline.deadline_type == deadline_type)
        if due_from is not None:
            query = query.filter(TaxDeadline.due_date >= due_from)
        if due_to is not None:
            query = query.filter(TaxDeadline.due_date <= due_to)
        if period is not None:
            query = query.filter(TaxDeadline.period == period)

        query = query.order_by(TaxDeadline.due_date.asc())
        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def count_filtered(
        self,
        *,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        period: Optional[str] = None,
    ) -> int:
        """Count non-deleted deadlines with optional status/type/date/period filters."""
        query = self._base_query()
        if status:
            query = query.filter(TaxDeadline.status == status)
        if deadline_type:
            query = query.filter(TaxDeadline.deadline_type == deadline_type)
        if due_from is not None:
            query = query.filter(TaxDeadline.due_date >= due_from)
        if due_to is not None:
            query = query.filter(TaxDeadline.due_date <= due_to)
        if period is not None:
            query = query.filter(TaxDeadline.period == period)
        return query.count()

    def list_overdue(self, reference_date: date) -> list[TaxDeadline]:
        """List pending, non-deleted deadlines overdue before reference_date."""
        return (
            self.db.query(TaxDeadline)
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.status == TaxDeadlineStatus.PENDING,
                TaxDeadline.due_date < reference_date,
            )
            .order_by(TaxDeadline.due_date.asc())
            .all()
        )

    def list_by_client_ids(
        self,
        client_ids: list[int],
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """List non-deleted deadlines for multiple clients with optional filters."""
        query = (
            self.db.query(TaxDeadline)
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.client_id.in_(client_ids),
            )
        )
        if status:
            query = query.filter(TaxDeadline.status == status)
        if deadline_type:
            query = query.filter(TaxDeadline.deadline_type == deadline_type)
        return query.order_by(TaxDeadline.due_date.asc()).all()

    def list_by_client(
        self,
        client_id: int,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        period: Optional[str] = None,
    ) -> list[TaxDeadline]:
        """List non-deleted deadlines for a client with optional filters."""
        query = (
            self.db.query(TaxDeadline)
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.client_id == client_id,
            )
        )
        if status:
            query = query.filter(TaxDeadline.status == status)
        if deadline_type:
            query = query.filter(TaxDeadline.deadline_type == deadline_type)
        if due_from is not None:
            query = query.filter(TaxDeadline.due_date >= due_from)
        if due_to is not None:
            query = query.filter(TaxDeadline.due_date <= due_to)
        if period is not None:
            query = query.filter(TaxDeadline.period == period)
        return query.order_by(TaxDeadline.due_date.asc()).all()

    def exists(
        self,
        client_id: int,
        deadline_type: DeadlineType,
        due_date: date,
    ) -> bool:
        """Return True if a non-deleted deadline with same client/type/due_date exists."""
        return (
            self.db.query(TaxDeadline.id)
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.client_id == client_id,
                TaxDeadline.deadline_type == deadline_type,
                TaxDeadline.due_date == due_date,
            )
            .first()
            is not None
        )
