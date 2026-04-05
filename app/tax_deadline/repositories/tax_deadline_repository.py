"""TaxDeadlineRepository — backward-compatible re-export.

Implementation is split into:
  - tax_deadline_query_repository.TaxDeadlineQueryRepository  (read + count)
  - tax_deadline_write_repository.TaxDeadlineWriteRepository  (write)

TaxDeadlineRepository is a unified facade over both for callers that need both.
New code should import from the split modules directly.
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_query_repository import TaxDeadlineQueryRepository
from app.tax_deadline.repositories.tax_deadline_write_repository import TaxDeadlineWriteRepository


class TaxDeadlineRepository:
    """Unified facade over query + write repositories."""

    def __init__(self, db: Session):
        self.db = db
        self._q = TaxDeadlineQueryRepository(db)
        self._w = TaxDeadlineWriteRepository(db)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, deadline_id: int) -> Optional[TaxDeadline]:
        return self._q.get_by_id(deadline_id)

    def list_pending_due_by_date(
        self,
        from_date: date,
        to_date: date,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[TaxDeadline]:
        return self._q.list_pending_due_by_date(from_date, to_date, limit=limit, offset=offset)

    def count_pending_due_by_date(self, from_date: date, to_date: date) -> int:
        return self._q.count_pending_due_by_date(from_date, to_date)

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
        return self._q.list_filtered(
            status=status,
            deadline_type=deadline_type,
            due_from=due_from,
            due_to=due_to,
            period=period,
            limit=limit,
            offset=offset,
        )

    def count_filtered(
        self,
        *,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        period: Optional[str] = None,
    ) -> int:
        return self._q.count_filtered(
            status=status,
            deadline_type=deadline_type,
            due_from=due_from,
            due_to=due_to,
            period=period,
        )

    def list_overdue(self, reference_date: date) -> list[TaxDeadline]:
        return self._q.list_overdue(reference_date)

    def list_by_business_ids(
        self,
        business_ids: list[int],
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        return self._q.list_by_business_ids(business_ids, status=status, deadline_type=deadline_type)

    def list_by_business(
        self,
        business_id: int,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        period: Optional[str] = None,
    ) -> list[TaxDeadline]:
        return self._q.list_by_business(
            business_id,
            status=status,
            deadline_type=deadline_type,
            due_from=due_from,
            due_to=due_to,
            period=period,
        )

    def exists(
        self,
        business_id: int,
        deadline_type: DeadlineType,
        due_date: date,
    ) -> bool:
        return self._q.exists(business_id, deadline_type, due_date)

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(
        self,
        business_id: int,
        deadline_type: DeadlineType,
        due_date: date,
        period: Optional[str] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        return self._w.create(
            business_id=business_id,
            deadline_type=deadline_type,
            due_date=due_date,
            period=period,
            payment_amount=payment_amount,
            description=description,
        )

    def update_status(
        self,
        deadline_id: int,
        status: TaxDeadlineStatus,
        **kwargs,
    ) -> Optional[TaxDeadline]:
        return self._w.update_status(deadline_id, status, **kwargs)

    def update(
        self,
        deadline_id: int,
        *,
        deadline_type: Optional[DeadlineType] = None,
        due_date: Optional[date] = None,
        period: Optional[str] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> Optional[TaxDeadline]:
        return self._w.update(
            deadline_id,
            deadline_type=deadline_type,
            due_date=due_date,
            period=period,
            payment_amount=payment_amount,
            description=description,
        )

    def delete(self, deadline_id: int, deleted_by: int) -> bool:
        return self._w.delete(deadline_id, deleted_by)
