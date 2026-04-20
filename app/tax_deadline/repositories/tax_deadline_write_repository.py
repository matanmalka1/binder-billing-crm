"""Write operations for TaxDeadline entities."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_query_repository import TaxDeadlineQueryRepository
from app.utils.time_utils import utcnow


class TaxDeadlineWriteRepository:
    def __init__(self, db: Session):
        self.db = db
        self._query = TaxDeadlineQueryRepository(db)

    # Expose read helpers needed by write operations
    def get_by_id(self, deadline_id: int) -> Optional[TaxDeadline]:
        return self._query.get_by_id(deadline_id)

    def create(
        self,
        client_record_id: int,
        deadline_type: DeadlineType,
        due_date: date,
        period: Optional[str] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        deadline = TaxDeadline(
            client_record_id=client_record_id,
            deadline_type=deadline_type,
            due_date=due_date,
            period=period,
            payment_amount=payment_amount,
            description=description,
            status=TaxDeadlineStatus.PENDING,
        )
        self.db.add(deadline)
        self.db.flush()
        return deadline

    _UNSET = object()

    def update_status(
        self,
        deadline_id: int,
        status: TaxDeadlineStatus,
        completed_at: Optional[datetime] = _UNSET,
        completed_by: Optional[int] = _UNSET,
    ) -> Optional[TaxDeadline]:
        deadline = self.get_by_id(deadline_id)
        if not deadline:
            return None
        deadline.status = status
        if completed_at is not self._UNSET:
            deadline.completed_at = completed_at
        if completed_by is not self._UNSET:
            deadline.completed_by = completed_by
        self.db.flush()
        return deadline

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
        deadline = self.get_by_id(deadline_id)
        if not deadline:
            return None
        if deadline_type:
            deadline.deadline_type = deadline_type
        if due_date:
            deadline.due_date = due_date
        if period is not None:
            deadline.period = period
        if payment_amount is not None:
            deadline.payment_amount = payment_amount
        if description is not None:
            deadline.description = description
        self.db.flush()
        return deadline

    def cancel_pending_by_client_record(self, client_record_id: int) -> int:
        """Set all PENDING deadlines for client_record_id to CANCELED. Returns count."""
        rows = (
            self.db.query(TaxDeadline)
            .filter(
                TaxDeadline.deleted_at.is_(None),
                TaxDeadline.client_record_id == client_record_id,
                TaxDeadline.status == TaxDeadlineStatus.PENDING,
            )
            .all()
        )
        for row in rows:
            row.status = TaxDeadlineStatus.CANCELED
        self.db.flush()
        return len(rows)

    def delete(self, deadline_id: int, deleted_by: int) -> bool:
        deadline = self.get_by_id(deadline_id)
        if not deadline:
            return False
        deadline.deleted_at = utcnow()
        deadline.deleted_by = deleted_by
        self.db.flush()
        return True
