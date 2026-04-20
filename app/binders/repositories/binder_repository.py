from datetime import date
from typing import Optional

from sqlalchemy import nullslast
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.binders.models.binder import Binder, BinderStatus
from app.utils.time_utils import utcnow


class BinderRepository(BaseRepository):
    """Data access layer for Binder entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    @staticmethod
    def _order_by_period_start(query, descending: bool):
        order_expr = Binder.period_start.desc() if descending else Binder.period_start.asc()
        return query.order_by(nullslast(order_expr), Binder.id.desc() if descending else Binder.id.asc())

    def create(
        self,
        client_id: int,
        binder_number: str,
        period_start: Optional[date],
        created_by: int,
        notes: Optional[str] = None,
        client_record_id: Optional[int] = None,
    ) -> Binder:
        """Create new binder."""
        binder = Binder(
            client_id=client_id,
            client_record_id=client_record_id,
            binder_number=binder_number,
            period_start=period_start,
            created_by=created_by,
            status=BinderStatus.IN_OFFICE,
            notes=notes,
        )
        self.db.add(binder)
        self.db.flush()
        return binder

    def get_by_id(self, binder_id: int) -> Optional[Binder]:
        """Retrieve binder by ID (excludes soft-deleted)."""
        return (
            self.db.query(Binder)
            .filter(Binder.id == binder_id, Binder.deleted_at.is_(None))
            .first()
        )

    def get_by_id_for_update(self, binder_id: int) -> Optional[Binder]:
        """Fetch with a row-level lock for status transitions."""
        return self._locked_first(
            self.db.query(Binder).filter(Binder.id == binder_id, Binder.deleted_at.is_(None))
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
        include_returned: bool = False,
    ) -> list[Binder]:
        """List binders with optional filters, sorting, and pagination.

        By default excludes RETURNED binders. Pass include_returned=True to
        include them (used when filtering explicitly by returned status).
        """
        from sqlalchemy import asc, desc

        query = self.db.query(Binder).filter(Binder.deleted_at.is_(None))
        if not include_returned:
            query = query.filter(Binder.status != BinderStatus.RETURNED)

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
        # NULLs in period_start (newly opened binders without material) sort last.
        query = query.order_by(nullslast(order_fn(col)))

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

    def list_open_binders(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """List open binders (status != RETURNED, not soft-deleted) with pagination."""
        query = (
            self.db.query(Binder)
            .filter(
                Binder.status != BinderStatus.RETURNED,
                Binder.deleted_at.is_(None),
            )
        )
        return self._paginate(self._order_by_period_start(query, descending=True), page, page_size)

    def count_open_binders(self) -> int:
        """Count open binders (not soft-deleted)."""
        return (
            self.db.query(Binder)
            .filter(
                Binder.status != BinderStatus.RETURNED,
                Binder.deleted_at.is_(None),
            )
            .count()
        )

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
            self._order_by_period_start(
                self.db.query(Binder).filter(
                    Binder.client_id == client_id,
                    Binder.deleted_at.is_(None),
                ),
                descending=False,
            )
            .all()
        )

    def list_by_client_record(self, client_record_id: int) -> list[Binder]:
        """Return all non-deleted binders for a client_record (all statuses)."""
        return (
            self._order_by_period_start(
                self.db.query(Binder).filter(
                    Binder.client_record_id == client_record_id,
                    Binder.deleted_at.is_(None),
                ),
                descending=False,
            )
            .all()
        )

    def get_active_by_client_record(self, client_record_id: int) -> Optional[Binder]:
        """Return the single open (IN_OFFICE) non-deleted binder for a client_record."""
        return (
            self.db.query(Binder)
            .filter(
                Binder.client_record_id == client_record_id,
                Binder.status == BinderStatus.IN_OFFICE,
                Binder.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_client_paginated(
        self,
        client_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """List all binders for a client (not soft-deleted) with pagination."""
        query = (
            self.db.query(Binder)
            .filter(
                Binder.client_id == client_id,
                Binder.deleted_at.is_(None),
            )
        )
        return self._paginate(self._order_by_period_start(query, descending=True), page, page_size)

    def count_by_client(self, client_id: int) -> int:
        """Count binders for a client (not soft-deleted)."""
        return (
            self.db.query(Binder)
            .filter(
                Binder.client_id == client_id,
                Binder.deleted_at.is_(None),
            )
            .count()
        )

    def get_active_by_client(self, client_id: int) -> Optional[Binder]:
        """Return the single open (IN_OFFICE) non-deleted binder for a client."""
        return (
            self.db.query(Binder)
            .filter(
                Binder.client_id == client_id,
                Binder.status == BinderStatus.IN_OFFICE,
                Binder.deleted_at.is_(None),
            )
            .first()
        )

    def count_all_by_client(self, client_id: int) -> int:
        """Count ALL binders for a client (including soft-deleted) for monotonic label seq."""
        return (
            self.db.query(Binder)
            .filter(Binder.client_id == client_id)
            .count()
        )

    def map_active_by_clients(self, client_ids: list[int]) -> dict[int, "Binder"]:
        """Return {client_id: binder} for the open (IN_OFFICE) binder of each client."""
        if not client_ids:
            return {}
        rows = (
            self.db.query(Binder)
            .filter(
                Binder.client_id.in_(client_ids),
                Binder.status == BinderStatus.IN_OFFICE,
                Binder.deleted_at.is_(None),
            )
            .all()
        )
        return {b.client_id: b for b in rows}

    def archive_in_office_by_client_record(self, client_record_id: int) -> int:
        rows = (
            self.db.query(Binder)
            .filter(
                Binder.client_record_id == client_record_id,
                Binder.deleted_at.is_(None),
                Binder.status.in_([
                    BinderStatus.IN_OFFICE,
                    BinderStatus.CLOSED_IN_OFFICE,
                ]),
            )
            .all()
        )
        for row in rows:
            row.status = BinderStatus.ARCHIVED_IN_OFFICE
        if rows:
            self.db.flush()
        return len(rows)

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
        self.db.flush()
        return True
