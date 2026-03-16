from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder_intake import BinderIntake


class BinderIntakeRepository:
    """Data access layer for BinderIntake entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        binder_id: int,
        received_at: date,
        received_by: int,
        notes: Optional[str] = None,
    ) -> BinderIntake:
        """Create a new intake record for a binder."""
        intake = BinderIntake(
            binder_id=binder_id,
            received_at=received_at,
            received_by=received_by,
            notes=notes,
        )
        self.db.add(intake)
        self.db.commit()
        self.db.refresh(intake)
        return intake

    def list_by_binder(self, binder_id: int) -> list[BinderIntake]:
        """Get all intakes for a binder, ordered by received_at ascending."""
        return (
            self.db.query(BinderIntake)
            .filter(BinderIntake.binder_id == binder_id)
            .order_by(BinderIntake.received_at.asc())
            .all()
        )
