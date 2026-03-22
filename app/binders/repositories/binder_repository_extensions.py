from sqlalchemy.orm import Session

from app.binders.models.binder import Binder, BinderStatus
from app.common.repositories import BaseRepository


class BinderRepositoryExtensions(BaseRepository):
    """Binder query extensions."""

    def __init__(self, db: Session):
        super().__init__(db)

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
            .order_by(Binder.period_start.desc(), Binder.id.desc())
        )
        return self._paginate(query, page, page_size)

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

    def list_by_client(
        self,
        client_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """List all binders for a client (not soft-deleted)."""
        query = (
            self.db.query(Binder)
            .filter(
                Binder.client_id == client_id,
                Binder.deleted_at.is_(None),
            )
            .order_by(Binder.period_start.desc(), Binder.id.desc())
        )
        return self._paginate(query, page, page_size)

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