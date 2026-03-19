from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus


class TaxDeadlineRepository:
    """Data access layer for TaxDeadline entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        business_id: int,
        deadline_type: DeadlineType,
        due_date: date,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> TaxDeadline:
        """Create a new tax deadline."""
        deadline = TaxDeadline(
            business_id=business_id,
            deadline_type=deadline_type,
            due_date=due_date,
            payment_amount=payment_amount,
            description=description,
            status=TaxDeadlineStatus.PENDING,
        )
        self.db.add(deadline)
        self.db.commit()
        self.db.refresh(deadline)
        return deadline

    def get_by_id(self, deadline_id: int) -> Optional[TaxDeadline]:
        """Retrieve a deadline by ID."""
        return self.db.query(TaxDeadline).filter(TaxDeadline.id == deadline_id).first()

    def update_status(
        self,
        deadline_id: int,
        status: TaxDeadlineStatus,
        completed_at: Optional[date] = None,
    ) -> Optional[TaxDeadline]:
        """Update deadline status (and optional completion date)."""
        deadline = self.get_by_id(deadline_id)
        if not deadline:
            return None

        deadline.status = status
        if completed_at:
            deadline.completed_at = completed_at

        self.db.commit()
        self.db.refresh(deadline)
        return deadline

    def list_pending_due_by_date(
        self,
        from_date: date,
        to_date: date,
    ) -> list[TaxDeadline]:
        """List pending deadlines due within [from_date, to_date]."""
        return (
            self.db.query(TaxDeadline)
            .filter(
                TaxDeadline.status == TaxDeadlineStatus.PENDING,
                TaxDeadline.due_date >= from_date,
                TaxDeadline.due_date <= to_date,
            )
            .order_by(TaxDeadline.due_date.asc())
            .all()
        )

    def list_overdue(self, reference_date: date) -> list[TaxDeadline]:
        """List pending deadlines overdue before reference_date."""
        return (
            self.db.query(TaxDeadline)
            .filter(
                TaxDeadline.status == TaxDeadlineStatus.PENDING,
                TaxDeadline.due_date < reference_date,
            )
            .order_by(TaxDeadline.due_date.asc())
            .all()
        )

    def list_by_business_ids(
        self,
        business_ids: list[int],
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """List deadlines for multiple clients with optional filters."""
        query = self.db.query(TaxDeadline).filter(TaxDeadline.business_id.in_(business_ids))

        if status:
            query = query.filter(TaxDeadline.status == status)

        if deadline_type:
            query = query.filter(TaxDeadline.deadline_type == deadline_type)

        return query.order_by(TaxDeadline.due_date.asc()).all()

    def list_by_business(
        self,
        business_id: int,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """List deadlines for a client with optional filters."""
        query = self.db.query(TaxDeadline).filter(TaxDeadline.business_id == business_id)

        if status:
            query = query.filter(TaxDeadline.status == status)

        if deadline_type:
            query = query.filter(TaxDeadline.deadline_type == deadline_type)

        return query.order_by(TaxDeadline.due_date.asc()).all()

    def update(
        self,
        deadline_id: int,
        *,
        deadline_type: Optional[DeadlineType] = None,
        due_date: Optional[date] = None,
        payment_amount: Optional[float] = None,
        description: Optional[str] = None,
    ) -> Optional[TaxDeadline]:
        """Update editable fields on a deadline."""
        deadline = self.get_by_id(deadline_id)
        if not deadline:
            return None

        if deadline_type:
            deadline.deadline_type = deadline_type
        if due_date:
            deadline.due_date = due_date
        if payment_amount is not None:
            deadline.payment_amount = payment_amount
        if description is not None:
            deadline.description = description

        self.db.commit()
        self.db.refresh(deadline)
        return deadline

    def exists(
        self,
        business_id: int,
        deadline_type: DeadlineType,
        due_date: date,
    ) -> bool:
        """Return True if a deadline with the same client/type/due_date already exists."""
        return (
            self.db.query(TaxDeadline.id)
            .filter(
                TaxDeadline.business_id == business_id,
                TaxDeadline.deadline_type == deadline_type,
                TaxDeadline.due_date == due_date,
            )
            .first()
            is not None
        )

    def delete(self, deadline_id: int) -> bool:
        """Delete a deadline by ID."""
        deadline = self.get_by_id(deadline_id)
        if not deadline:
            return False

        self.db.delete(deadline)
        self.db.commit()
        return True
