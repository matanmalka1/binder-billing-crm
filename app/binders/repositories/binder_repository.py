from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.binders.models.binder import Binder, BinderStatus
from app.utils.time_utils import utcnow


class BinderRepository(BaseRepository):
    """Data access layer for Binder entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        client_id: int,
        binder_number: str,
        period_start: date,
        created_by: int,
        notes: Optional[str] = None,
    ) -> Binder:
        """Create new binder."""
        binder = Binder(
            client_id=client_id,
            binder_number=binder_number,
            period_start=period_start,
            created_by=created_by,
            status=BinderStatus.IN_OFFICE,
            notes=notes,
        )
        self.db.add(binder)
        self.db.commit()
        self.db.refresh(binder)
        return binder

    def get_by_id(self, binder_id: int) -> Optional[Binder]:
        """Retrieve binder by ID (excludes soft-deleted)."""
        return (
            self.db.query(Binder)
            .filter(Binder.id == binder_id, Binder.deleted_at.is_(None))
            .first()
        )

    def get_active_by_number(self, binder_number: str) -> Optional[Binder]:
        """Get active (non-returned) binder by number (excludes soft-deleted)."""
        return (
            self.db.query(Binder)
            .filter(
                Binder.binder_number == binder_number,
                Binder.status != BinderStatus.RETURNED,
                Binder.deleted_at.is_(None),
            )
            .first()
        )

    def list_active(
        self,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        binder_number: Optional[str] = None,
        sort_by: str = "period_start",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 1000,
    ) -> list[Binder]:
        """List active binders with optional filters, sorting, and pagination."""
        from sqlalchemy import asc, desc

        query = self.db.query(Binder).filter(
            Binder.status != BinderStatus.RETURNED,
            Binder.deleted_at.is_(None),
        )

        if client_id:
            query = query.filter(Binder.client_id == client_id)

        if status:
            query = query.filter(Binder.status == status)

        if binder_number:
            query = query.filter(Binder.binder_number.ilike(f"%{binder_number.strip()}%"))

        sort_col_map = {
            "period_start": Binder.period_start,
            "days_in_office": Binder.period_start,  # older period_start → more days
            "status": Binder.status,
        }
        col = sort_col_map.get(sort_by, Binder.period_start)
        effective_dir = sort_dir
        if sort_by == "days_in_office":
            effective_dir = "asc" if sort_dir == "desc" else "desc"

        order_fn = asc if effective_dir == "asc" else desc
        query = query.order_by(order_fn(col))

        return self._paginate(query, page, page_size)

    def count_active(
        self,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count active binders with optional filters."""
        query = self.db.query(Binder).filter(
            Binder.status != BinderStatus.RETURNED,
            Binder.deleted_at.is_(None),
        )

        if client_id:
            query = query.filter(Binder.client_id == client_id)

        if status:
            query = query.filter(Binder.status == status)

        return query.count()

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
        return (
            self.db.query(Binder)
            .filter(Binder.status == status, Binder.deleted_at.is_(None))
            .count()
        )

    def list_by_client(self, client_id: int) -> list[Binder]:
        """Return all non-deleted binders for a client (all statuses)."""
        return (
            self.db.query(Binder)
            .filter(Binder.client_id == client_id, Binder.deleted_at.is_(None))
            .order_by(Binder.period_start.asc())
            .all()
        )

    def soft_delete(self, binder_id: int, deleted_by: int) -> bool:
        """Soft-delete a binder: marks RETURNED, sets returned_at if unset, records deleted_at/deleted_by."""
        binder = self.db.query(Binder).filter(Binder.id == binder_id).first()
        if not binder:
            return False
        binder.status = BinderStatus.RETURNED
        if binder.returned_at is None:
            binder.returned_at = date.today()
        binder.deleted_at = utcnow()
        binder.deleted_by = deleted_by
        self.db.commit()
        return True