"""Read-only list queries for BusinessRepository — split to stay under 150-line limit."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.businesses.models.business import Business


class BusinessRepositoryRead(BaseRepository[Business]):
    """List and count queries for Business entities."""

    model = Business

    def __init__(self, db: Session):
        super().__init__(db)

    def _build_base_stmt(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
    ):
        """Shared filter chain for Business-only list() and count()."""
        stmt = select(Business).where(Business.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Business.status == status)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                Business.business_name.ilike(term)
                | cast(Business.id, String).ilike(term)
            )
        return stmt

    def list(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Business]:
        stmt = self._build_base_stmt(status, entity_type, search).order_by(
            Business.opened_at.desc()
        )
        stmt = self.apply_pagination(stmt, page, page_size)
        return self.db.scalars(stmt).all()

    def count(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        base = self._build_base_stmt(status, entity_type, search)
        stmt = select(func.count()).select_from(base.subquery())
        return self.db.scalar(stmt)

    def list_by_legal_entity(
        self, legal_entity_id: int, page: int = 1, page_size: int = 20
    ) -> list[Business]:
        stmt = (
            select(Business)
            .where(
                Business.legal_entity_id == legal_entity_id,
                Business.deleted_at.is_(None),
            )
            .order_by(Business.opened_at.asc())
        )
        stmt = self.apply_pagination(stmt, page, page_size)
        return self.db.scalars(stmt).all()

    def count_by_legal_entity(self, legal_entity_id: int) -> int:
        return self.db.scalar(
            select(func.count(Business.id)).where(
                Business.legal_entity_id == legal_entity_id,
                Business.deleted_at.is_(None),
            )
        )

    def list_by_legal_entity_including_deleted(
        self, legal_entity_id: int
    ) -> list[Business]:
        return self.db.scalars(
            select(Business)
            .where(Business.legal_entity_id == legal_entity_id)
            .order_by(Business.deleted_at.asc().nullsfirst(), Business.opened_at.asc())
        ).all()

    def list_by_legal_entity_ids(self, legal_entity_ids: list[int]) -> list[Business]:
        if not legal_entity_ids:
            return []
        return self.db.scalars(
            select(Business).where(
                Business.legal_entity_id.in_(legal_entity_ids),
                Business.deleted_at.is_(None),
            )
        ).all()

    def list_by_ids(self, business_ids: list[int]) -> list[Business]:
        if not business_ids:
            return []
        return self.db.scalars(
            select(Business).where(
                Business.id.in_(business_ids), Business.deleted_at.is_(None)
            )
        ).all()

    def list_all(self, status: Optional[str] = None) -> list[Business]:
        """List all active businesses. No pagination — internal aggregation use only."""
        stmt = select(Business).where(Business.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Business.status == status)
        return self.db.scalars(stmt.order_by(Business.opened_at.desc())).all()
