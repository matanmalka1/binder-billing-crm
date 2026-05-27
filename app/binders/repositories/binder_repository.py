import datetime as _dt
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import asc, desc, extract, func, nullslast, or_, select
from sqlalchemy.orm import Session

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.repositories.base_repository import BaseRepository
from app.utils.time_utils import utcnow


@dataclass(frozen=True)
class BinderListRow:
    id: int
    client_record_id: int
    office_client_number: int | None
    client_name: str
    client_id_number: str
    binder_number: str
    status: BinderStatus
    period_start: date | None
    period_end: date | None
    ready_for_pickup_at: datetime | None
    returned_at: date | None
    pickup_person_name: str | None
    notes: str | None
    created_at: datetime


class BinderRepository(BaseRepository[Binder]):
    """Data access layer for Binder entities."""

    model = Binder

    def __init__(self, db: Session):
        super().__init__(db)

    @staticmethod
    def _order_by_period_start(query, descending: bool):
        order_expr = Binder.period_start.desc() if descending else Binder.period_start.asc()
        return query.order_by(
            nullslast(order_expr), Binder.id.desc() if descending else Binder.id.asc()
        )

    def _active_client_stmt(self):
        return scope_to_active_clients_stmt(select(Binder), Binder)

    def _filtered_active_stmt(
        self,
        stmt,
        *,
        client_record_id: int | None = None,
        status: str | None = None,
        include_returned: bool = True,
        query: str | None = None,
        client_name_filter: str | None = None,
        binder_number: str | None = None,
        year: int | None = None,
        include_legal_entity: bool = False,
    ):
        needs_legal_entity = include_legal_entity or bool(query or client_name_filter)
        stmt = scope_to_active_clients_stmt(stmt, Binder).where(Binder.deleted_at.is_(None))
        if needs_legal_entity:
            stmt = stmt.outerjoin(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)

        if client_record_id:
            stmt = stmt.where(Binder.client_record_id == client_record_id)
        if status:
            stmt = stmt.where(Binder.status == status)
        elif not include_returned:
            stmt = stmt.where(Binder.status != BinderStatus.RETURNED)

        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Binder.binder_number.ilike(pattern),
                    LegalEntity.official_name.ilike(pattern),
                )
            )
        if client_name_filter:
            stmt = stmt.where(LegalEntity.official_name.ilike(f"%{client_name_filter.strip()}%"))
        if binder_number:
            stmt = stmt.where(Binder.binder_number.ilike(f"%{binder_number.strip()}%"))
        if year:
            stmt = stmt.where(extract("year", Binder.period_start) == year)

        return stmt

    @staticmethod
    def _order_active_paginated_stmt(stmt, *, sort_by: str, sort_dir: str):
        order_fn = asc if sort_dir == "asc" else desc
        effective_sort_dir = sort_dir
        if sort_by == "days_in_office":
            effective_sort_dir = "asc" if sort_dir == "desc" else "desc"
            order_fn = asc if effective_sort_dir == "asc" else desc

        if sort_by == "client_name":
            name_order = order_fn(LegalEntity.official_name)
            period_order = (asc if sort_dir == "asc" else desc)(Binder.period_start)
            return stmt.order_by(
                nullslast(name_order),
                nullslast(period_order),
                Binder.id.asc() if sort_dir == "asc" else Binder.id.desc(),
            )

        sort_col_map = {
            "period_start": Binder.period_start,
            "days_in_office": Binder.period_start,
            "status": Binder.status,
        }
        col = sort_col_map.get(sort_by, Binder.period_start)
        return stmt.order_by(nullslast(order_fn(col)))

    def create(
        self,
        client_record_id: int,
        binder_number: str,
        period_start: date | None,
        created_by: int,
        notes: str | None = None,
    ) -> Binder:
        """Create new binder."""
        binder = Binder(
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

    def get_active_by_number(self, binder_number: str) -> Binder | None:
        """Get active (non-returned) binder by number (excludes soft-deleted)."""
        return self.db.scalars(
            select(Binder).where(
                Binder.binder_number == binder_number,
                Binder.status != BinderStatus.RETURNED,
                Binder.deleted_at.is_(None),
            )
        ).first()

    def list_active(
        self,
        client_record_id: int | None = None,
        status: str | None = None,
        binder_number: str | None = None,
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

        stmt = self._active_client_stmt().where(Binder.deleted_at.is_(None))
        if not include_returned:
            stmt = stmt.where(Binder.status != BinderStatus.RETURNED)

        if client_record_id:
            stmt = stmt.where(Binder.client_record_id == client_record_id)

        if status:
            stmt = stmt.where(Binder.status == status)

        if binder_number:
            stmt = stmt.where(Binder.binder_number.ilike(f"%{binder_number.strip()}%"))

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
        stmt = stmt.order_by(nullslast(order_fn(col)))

        stmt = self.apply_pagination(stmt, page, page_size)
        return self.db.scalars(stmt).all()

    def list_active_paginated(
        self,
        *,
        client_record_id: int | None = None,
        status: str | None = None,
        include_returned: bool = True,
        query: str | None = None,
        client_name_filter: str | None = None,
        binder_number: str | None = None,
        year: int | None = None,
        sort_by: str = "period_start",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Binder], int]:
        include_legal_entity = sort_by == "client_name"
        base_kwargs = {
            "client_record_id": client_record_id,
            "status": status,
            "include_returned": include_returned,
            "query": query,
            "client_name_filter": client_name_filter,
            "binder_number": binder_number,
            "year": year,
            "include_legal_entity": include_legal_entity,
        }
        count_stmt = self._filtered_active_stmt(
            select(func.count(Binder.id)),
            **base_kwargs,
        )
        stmt = self._filtered_active_stmt(select(Binder), **base_kwargs)
        stmt = self._order_active_paginated_stmt(
            stmt,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        stmt = self.apply_pagination(stmt, page, page_size)
        return list(self.db.scalars(stmt).all()), int(self.db.scalar(count_stmt) or 0)

    def list_active_paginated_projected(
        self,
        *,
        client_record_id: int | None = None,
        status: str | None = None,
        include_returned: bool = True,
        query: str | None = None,
        client_name_filter: str | None = None,
        binder_number: str | None = None,
        year: int | None = None,
        sort_by: str = "period_start",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BinderListRow], int]:
        # LegalEntity join is needed for count only when filtering/sorting by client_name.
        # The projection SELECT always needs it to populate client fields.
        needs_join_for_filter = sort_by == "client_name" or bool(query or client_name_filter)
        filter_kwargs = dict(
            client_record_id=client_record_id,
            status=status,
            include_returned=include_returned,
            query=query,
            client_name_filter=client_name_filter,
            binder_number=binder_number,
            year=year,
        )

        count_stmt = self._filtered_active_stmt(
            select(func.count(Binder.id)),
            **filter_kwargs,
            include_legal_entity=needs_join_for_filter,
        )

        proj_stmt = self._filtered_active_stmt(
            select(
                Binder.id,
                Binder.client_record_id,
                ClientRecord.office_client_number,
                LegalEntity.official_name.label("client_name"),
                LegalEntity.id_number.label("client_id_number"),
                Binder.binder_number,
                Binder.status,
                Binder.period_start,
                Binder.period_end,
                Binder.ready_for_pickup_at,
                Binder.returned_at,
                Binder.pickup_person_name,
                Binder.notes,
                Binder.created_at,
            ),
            **filter_kwargs,
            include_legal_entity=True,
        )
        proj_stmt = self._order_active_paginated_stmt(proj_stmt, sort_by=sort_by, sort_dir=sort_dir)
        proj_stmt = self.apply_pagination(proj_stmt, page, page_size)

        rows = [
            BinderListRow(
                id=row.id,
                client_record_id=row.client_record_id,
                office_client_number=row.office_client_number,
                client_name=row.client_name,
                client_id_number=row.client_id_number,
                binder_number=row.binder_number,
                status=row.status,
                period_start=row.period_start,
                period_end=row.period_end,
                ready_for_pickup_at=row.ready_for_pickup_at,
                returned_at=row.returned_at,
                pickup_person_name=row.pickup_person_name,
                notes=row.notes,
                created_at=row.created_at,
            )
            for row in self.db.execute(proj_stmt).all()
        ]
        return rows, int(self.db.scalar(count_stmt) or 0)

    def count_by_status_filtered(
        self,
        *,
        client_record_id: int | None = None,
        query: str | None = None,
        client_name_filter: str | None = None,
        binder_number: str | None = None,
        year: int | None = None,
    ) -> dict[str, int]:
        stmt = self._filtered_active_stmt(
            select(Binder.status, func.count(Binder.id)),
            client_record_id=client_record_id,
            query=query,
            client_name_filter=client_name_filter,
            binder_number=binder_number,
            year=year,
        ).group_by(Binder.status)
        counts = {status.value: 0 for status in BinderStatus}
        total = 0
        for status, count in self.db.execute(stmt).all():
            value = status.value if isinstance(status, BinderStatus) else str(status)
            counts[value] = int(count)
            total += int(count)
        return {"total": total, **counts}

    def count_active(
        self,
        client_record_id: int | None = None,
        status: str | None = None,
    ) -> int:
        """Count active binders with optional filters."""
        stmt = scope_to_active_clients_stmt(select(func.count(Binder.id)), Binder).where(
            Binder.status != BinderStatus.RETURNED,
            Binder.deleted_at.is_(None),
        )

        if client_record_id:
            stmt = stmt.where(Binder.client_record_id == client_record_id)

        if status:
            stmt = stmt.where(Binder.status == status)

        return self.db.scalar(stmt)

    def list_open_binders(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """List open binders (status != RETURNED, not soft-deleted) with pagination."""
        stmt = self._active_client_stmt().where(
            Binder.status != BinderStatus.RETURNED,
            Binder.deleted_at.is_(None),
        )
        stmt = self._order_by_period_start(stmt, descending=True)
        stmt = self.apply_pagination(stmt, page, page_size)
        return self.db.scalars(stmt).all()

    def count_open_binders(self) -> int:
        """Count open binders (not soft-deleted)."""
        stmt = scope_to_active_clients_stmt(select(func.count(Binder.id)), Binder).where(
            Binder.status != BinderStatus.RETURNED,
            Binder.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def update_status(
        self,
        binder_id: int,
        new_status: BinderStatus,
        binder: Binder | None = None,
        **additional_fields,
    ) -> Binder | None:
        """Update binder status and optional fields."""
        binder = binder or self.get_by_id(binder_id)
        return self._update_status(binder, new_status, **additional_fields)

    def count_by_status(self, status: BinderStatus) -> int:
        """Count binders by status."""
        stmt = scope_to_active_clients_stmt(select(func.count(Binder.id)), Binder).where(
            Binder.status == status, Binder.deleted_at.is_(None)
        )
        return self.db.scalar(stmt)

    def list_by_client_record(self, client_record_id: int) -> list[Binder]:
        """Return all non-deleted binders for a client_record (all statuses)."""
        return self.db.scalars(
            select(Binder)
            .where(
                Binder.client_record_id == client_record_id,
                Binder.deleted_at.is_(None),
            )
            .order_by(
                nullslast(Binder.period_start.asc()),
                Binder.id.asc(),
            )
        ).all()

    def list_by_client_record_paginated(
        self,
        client_record_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """Return paginated non-deleted binders for a client_record (all statuses)."""
        stmt = (
            select(Binder)
            .where(
                Binder.client_record_id == client_record_id,
                Binder.deleted_at.is_(None),
            )
            .order_by(
                nullslast(Binder.period_start.asc()),
                Binder.id.asc(),
            )
        )
        return self.db.scalars(self.apply_pagination(stmt, page, page_size)).all()

    def count_by_client_record(self, client_record_id: int) -> int:
        """Count non-deleted binders for a client_record (all statuses)."""
        return self.db.scalar(
            select(func.count(Binder.id)).where(
                Binder.client_record_id == client_record_id,
                Binder.deleted_at.is_(None),
            )
        )

    def get_active_by_client_record(self, client_record_id: int) -> Binder | None:
        """Return the single open (IN_OFFICE) non-deleted binder for a client_record."""
        stmt = self._active_client_stmt().where(
            Binder.client_record_id == client_record_id,
            Binder.status == BinderStatus.IN_OFFICE,
            Binder.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def list_by_client_paginated(
        self,
        client_record_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """List all binders for a client (not soft-deleted) with pagination."""
        stmt = self._active_client_stmt().where(
            Binder.client_record_id == client_record_id,
            Binder.deleted_at.is_(None),
        )
        stmt = self._order_by_period_start(stmt, descending=True)
        stmt = self.apply_pagination(stmt, page, page_size)
        return self.db.scalars(stmt).all()

    def count_by_client(self, client_record_id: int) -> int:
        """Count binders for a client (not soft-deleted)."""
        stmt = scope_to_active_clients_stmt(select(func.count(Binder.id)), Binder).where(
            Binder.client_record_id == client_record_id,
            Binder.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def count_all_by_client(self, client_record_id: int) -> int:
        """Count ALL binders for a client (including soft-deleted) for monotonic label seq."""
        return self.db.scalar(
            select(func.count(Binder.id)).where(Binder.client_record_id == client_record_id)
        )

    def map_active_by_clients(self, client_record_ids: list[int]) -> dict[int, "Binder"]:
        """Return {client_record_id: binder} for the open (IN_OFFICE) binder of each client."""
        if not client_record_ids:
            return {}
        stmt = self._active_client_stmt().where(
            Binder.client_record_id.in_(client_record_ids),
            Binder.status == BinderStatus.IN_OFFICE,
            Binder.deleted_at.is_(None),
        )
        rows = self.db.scalars(stmt).all()
        for row in rows:
            row.client_record_id = row.client_record_id
        return {b.client_record_id: b for b in rows}

    def close_in_office_by_client_record(self, client_record_id: int) -> int:
        rows = self.db.scalars(
            select(Binder).where(
                Binder.client_record_id == client_record_id,
                Binder.deleted_at.is_(None),
                Binder.status == BinderStatus.IN_OFFICE,
            )
        ).all()
        for row in rows:
            row.status = BinderStatus.CLOSED_IN_OFFICE
        if rows:
            self.db.flush()
        return len(rows)

    def list_overdue_pickup(self, overdue_days: int = 30, limit: int = 50) -> list[Binder]:
        """Return READY_FOR_PICKUP binders where ready_for_pickup_at is older than overdue_days."""
        cutoff = utcnow() - _dt.timedelta(days=overdue_days)
        stmt = (
            self._active_client_stmt()
            .where(
                Binder.status == BinderStatus.READY_FOR_PICKUP,
                Binder.ready_for_pickup_at.isnot(None),
                Binder.ready_for_pickup_at <= cutoff,
                Binder.deleted_at.is_(None),
            )
            .order_by(Binder.ready_for_pickup_at.asc())
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def soft_delete(self, binder_id: int, deleted_by: int | None = None) -> bool:
        """Soft-delete a binder: marks RETURNED, sets returned_at if unset, records deleted_at/deleted_by."""
        binder = self.db.scalars(select(Binder).where(Binder.id == binder_id)).first()
        if not binder:
            return False
        binder.status = BinderStatus.RETURNED
        if binder.returned_at is None:
            binder.returned_at = date.today()
        binder.deleted_at = utcnow()
        binder.deleted_by = deleted_by
        self.db.flush()
        return True
