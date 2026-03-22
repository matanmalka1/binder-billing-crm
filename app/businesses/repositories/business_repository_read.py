"""Read-only list queries for BusinessRepository — split to stay under 150-line limit."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Query as SAQuery, Session

from app.common.repositories import BaseRepository
from app.businesses.models.business import Business


class BusinessRepositoryRead(BaseRepository):
    """List and count queries for Business entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def _build_base_query(
        self,
        status: Optional[str] = None,
        business_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> SAQuery:
        """Shared filter chain for list() and count()."""
        from app.clients.models.client import Client

        query = (
            self.db.query(Business)
            .join(Client, Client.id == Business.client_id)
            .filter(
                Business.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
        )
        if status:
            query = query.filter(Business.status == status)
        if business_type:
            query = query.filter(Business.business_type == business_type)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Business.business_name.ilike(term)
                | Client.full_name.ilike(term)
                | Client.id_number.ilike(term)
            )
        return query

    def list_by_client(self, client_id: int, page: int = 1, page_size: int = 20) -> list[Business]:
        """List active businesses for a client (paginated)."""
        query = (
            self.db.query(Business)
            .filter(Business.client_id == client_id, Business.deleted_at.is_(None))
            .order_by(Business.opened_at.asc())
        )
        return self._paginate(query, page, page_size)

    def count_by_client(self, client_id: int) -> int:
        return (
            self.db.query(Business)
            .filter(Business.client_id == client_id, Business.deleted_at.is_(None))
            .count()
        )

    def list_by_client_including_deleted(self, client_id: int) -> list[Business]:
        return (
            self.db.query(Business)
            .filter(Business.client_id == client_id)
            .order_by(Business.deleted_at.asc().nullsfirst(), Business.opened_at.asc())
            .all()
        )

    def list(
        self,
        status: Optional[str] = None,
        business_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Business]:
        query = self._build_base_query(status, business_type, search)
        return self._paginate(query.order_by(Business.opened_at.desc()), page, page_size)

    def count(
        self,
        status: Optional[str] = None,
        business_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        return self._build_base_query(status, business_type, search).count()

    def list_by_ids(self, business_ids: list[int]) -> list[Business]:
        if not business_ids:
            return []
        return (
            self.db.query(Business)
            .filter(Business.id.in_(business_ids), Business.deleted_at.is_(None))
            .all()
        )

    def list_all(self, status: Optional[str] = None) -> list[Business]:
        """List all active businesses. No pagination — internal aggregation use only."""
        query = self.db.query(Business).filter(Business.deleted_at.is_(None))
        if status:
            query = query.filter(Business.status == status)
        return query.order_by(Business.opened_at.desc()).all()
