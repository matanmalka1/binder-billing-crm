from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.binders.models.binder import Binder, BinderStatus, BinderType


class BinderRepository(BaseRepository):
    """Data access layer for Binder entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        client_id: int,
        binder_number: str,
        binder_type: BinderType,
        received_at: date,
        received_by: int,
        notes: Optional[str] = None,
    ) -> Binder:
        """Create new binder (intake flow)."""
        binder = Binder(
            client_id=client_id,
            binder_number=binder_number,
            binder_type=binder_type,
            received_at=received_at,
            received_by=received_by,
            status=BinderStatus.IN_OFFICE,
            notes=notes,
        )
        self.db.add(binder)
        self.db.commit()
        self.db.refresh(binder)
        return binder

    def get_by_id(self, binder_id: int) -> Optional[Binder]:
        """Retrieve binder by ID."""
        return self.db.query(Binder).filter(Binder.id == binder_id).first()

    def get_active_by_number(self, binder_number: str) -> Optional[Binder]:
        """Get active (non-returned) binder by number."""
        return (
            self.db.query(Binder)
            .filter(
                Binder.binder_number == binder_number,
                Binder.status != BinderStatus.RETURNED,
            )
            .first()
        )

    def list_active(
        self,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> list[Binder]:
        """List active binders with optional filters."""
        query = self.db.query(Binder).filter(Binder.status != BinderStatus.RETURNED)

        if client_id:
            query = query.filter(Binder.client_id == client_id)

        if status:
            query = query.filter(Binder.status == status)

        return query.all()

    def update_status(
        self,
        binder_id: int,
        new_status: BinderStatus,
        binder: Optional[Binder] = None,
        **additional_fields,
    ) -> Optional[Binder]:
        """Update binder status and optional fields."""
        binder = binder or self.get_by_id(binder_id)
        return self._update_status(binder, new_status, **additional_fields)

    def count_by_status(self, status: BinderStatus) -> int:
        """Count binders by status."""
        return self.db.query(Binder).filter(Binder.status == status).count()
