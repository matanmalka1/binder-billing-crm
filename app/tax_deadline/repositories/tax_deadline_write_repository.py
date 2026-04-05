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
        business_id: int,
        deadline_type: DeadlineType,
        due_date: date,
        period: Optional[str] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        deadline = TaxDeadline(
            business_id=business_id,
            deadline_type=deadline_type,
            due_date=due_date,
            period=period,
            payment_amount=payment_amount,
            description=description,
            status=TaxDeadlineStatus.PENDING,
        )
        self.db.add(deadline)
        self.db.commit()
        self.db.refresh(deadline)
        return deadline

    def update_status(
        self,
        deadline_id: int,
        status: TaxDeadlineStatus,
        completed_at: Optional[datetime] = None,
        completed_by: Optional[int] = None,
    ) -> Optional[TaxDeadline]:
        deadline = self.get_by_id(deadline_id)
        if not deadline:
            return None
        deadline.status = status
        if completed_at:
            deadline.completed_at = completed_at
        if completed_by is not None:
            deadline.completed_by = completed_by
        self.db.commit()
        self.db.refresh(deadline)
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
        self.db.commit()
        self.db.refresh(deadline)
        return deadline

    def delete(self, deadline_id: int, deleted_by: int) -> bool:
        deadline = self.get_by_id(deadline_id)
        if not deadline:
            return False
        deadline.deleted_at = utcnow()
        deadline.deleted_by = deleted_by
        self.db.commit()
        return True
