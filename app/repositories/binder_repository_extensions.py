from datetime import date

from sqlalchemy.orm import Session

from app.models import Binder, BinderStatus
from app.services.sla_service import SLAService


class BinderRepositoryExtensions:
    """Sprint 2 binder query extensions."""

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

    def list_overdue_candidates(
        self,
        reference_date: date,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """
        List binders where expected_return_at < reference_date.
        
        Note: Overdue status is derived at read time.
        """
        query = (
            self.db.query(Binder)
            .filter(SLAService.overdue_filter(reference_date))
            .order_by(Binder.expected_return_at.asc(), Binder.id.desc())
        )
        
        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()

    def count_overdue_candidates(self, reference_date: date) -> int:
        """Count overdue candidate binders."""
        return (
            self.db.query(Binder)
            .filter(SLAService.overdue_filter(reference_date))
            .count()
        )

    def list_due_today(
        self,
        reference_date: date,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Binder]:
        """List binders due on reference_date."""
        query = (
            self.db.query(Binder)
            .filter(SLAService.due_today_filter(reference_date))
            .order_by(Binder.id.desc())
        )
        
        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()

    def count_due_today(self, reference_date: date) -> int:
        """Count binders due today."""
        return (
            self.db.query(Binder)
            .filter(SLAService.due_today_filter(reference_date))
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
