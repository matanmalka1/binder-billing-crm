from sqlalchemy.orm import Session

from app.binders.models.binder import Binder, BinderStatus


class BinderRepositoryExtensions:
    """Binder query extensions."""

    def __init__(self, db: Session):
        self.db = db

    def list_open_binders(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """List open binders (status != RETURNED) with pagination."""
        query = (
            self.db.query(Binder)
            .filter(Binder.status != BinderStatus.RETURNED)
            .order_by(Binder.received_at.desc(), Binder.id.desc())
        )

        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()

    def count_open_binders(self) -> int:
        """Count open binders."""
        return (
            self.db.query(Binder)
            .filter(Binder.status != BinderStatus.RETURNED)
            .count()
        )

    def list_by_client(
        self,
        client_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """List all binders for a client."""
        query = (
            self.db.query(Binder)
            .filter(Binder.client_id == client_id)
            .order_by(Binder.received_at.desc(), Binder.id.desc())
        )

        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()

    def count_by_client(self, client_id: int) -> int:
        """Count binders for a client."""
        return (
            self.db.query(Binder)
            .filter(Binder.client_id == client_id)
            .count()
        )
