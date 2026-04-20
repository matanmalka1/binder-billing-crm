"""Read-only list queries for BusinessRepository — split to stay under 150-line limit."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import String, cast
from sqlalchemy.orm import Query as SAQuery, Session, joinedload

from app.common.repositories.base_repository import BaseRepository
from app.businesses.models.business import Business
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.client_record import ClientRecord
from app.clients.models.person_legal_entity_link import PersonLegalEntityLink


class BusinessRepositoryRead(BaseRepository):
    """List and count queries for Business entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def _build_base_query(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> SAQuery:
        """Shared filter chain for list() and count()."""
        from app.clients.models.legal_entity import LegalEntity
        from app.clients.models.client_record import ClientRecord

        query = (
            self.db.query(Business)
            .join(ClientRecord, ClientRecord.legal_entity_id == Business.legal_entity_id)
            .join(LegalEntity, LegalEntity.id == Business.legal_entity_id)
            .filter(
                Business.deleted_at.is_(None),
                ClientRecord.deleted_at.is_(None),
            )
        )
        if status:
            query = query.filter(Business.status == status)
        if entity_type:
            query = query.filter(LegalEntity.entity_type == entity_type)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Business.business_name.ilike(term)
                | LegalEntity.official_name.ilike(term)
                | LegalEntity.id_number.ilike(term)
                | cast(LegalEntity.id, String).ilike(term)
                | cast(Business.id, String).ilike(term)
            )
        return query

    def list_by_client(self, client_id: int, page: int = 1, page_size: int = 20) -> list[Business]:
        """List active businesses for a client (paginated)."""
        query = (
            self.db.query(Business)
            .join(ClientRecord, ClientRecord.legal_entity_id == Business.legal_entity_id)
            .filter(ClientRecord.id == client_id, Business.deleted_at.is_(None))
            .order_by(Business.opened_at.asc())
        )
        return self._paginate(query, page, page_size)

    def count_by_client(self, client_id: int) -> int:
        return (
            self.db.query(Business)
            .join(ClientRecord, ClientRecord.legal_entity_id == Business.legal_entity_id)
            .filter(ClientRecord.id == client_id, Business.deleted_at.is_(None))
            .count()
        )

    def list_by_client_including_deleted(self, client_id: int) -> list[Business]:
        return (
            self.db.query(Business)
            .join(ClientRecord, ClientRecord.legal_entity_id == Business.legal_entity_id)
            .filter(ClientRecord.id == client_id)
            .order_by(Business.deleted_at.asc().nullsfirst(), Business.opened_at.asc())
            .all()
        )

    def list(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Business]:
        query = self._build_base_query(status, entity_type, search)
        return self._paginate(query.order_by(Business.opened_at.desc()), page, page_size)

    def count(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        return self._build_base_query(status, entity_type, search).count()

    def list_by_client_ids(self, client_ids: list[int]) -> list[Business]:
        if not client_ids:
            return []
        return (
            self.db.query(Business)
            .join(ClientRecord, ClientRecord.legal_entity_id == Business.legal_entity_id)
            .filter(ClientRecord.id.in_(client_ids), Business.deleted_at.is_(None))
            .all()
        )

    def list_by_legal_entity(self, legal_entity_id: int, page: int = 1, page_size: int = 20) -> list[Business]:
        query = (
            self.db.query(Business)
            .filter(Business.legal_entity_id == legal_entity_id, Business.deleted_at.is_(None))
            .order_by(Business.opened_at.asc())
        )
        return self._paginate(query, page, page_size)

    def count_by_legal_entity(self, legal_entity_id: int) -> int:
        return (
            self.db.query(Business)
            .filter(Business.legal_entity_id == legal_entity_id, Business.deleted_at.is_(None))
            .count()
        )

    def list_by_legal_entity_including_deleted(self, legal_entity_id: int) -> list[Business]:
        return (
            self.db.query(Business)
            .filter(Business.legal_entity_id == legal_entity_id)
            .order_by(Business.deleted_at.asc().nullsfirst(), Business.opened_at.asc())
            .all()
        )

    def list_by_legal_entity_ids(self, legal_entity_ids: list[int]) -> list[Business]:
        if not legal_entity_ids:
            return []
        return (
            self.db.query(Business)
            .filter(Business.legal_entity_id.in_(legal_entity_ids), Business.deleted_at.is_(None))
            .all()
        )

    def list_by_ids(self, business_ids: list[int]) -> list[Business]:
        if not business_ids:
            return []
        from app.clients.models.person import Person
        return (
            self.db.query(Business)
            .options(
                joinedload(Business.legal_entity)
                .joinedload(LegalEntity.person_links)
                .joinedload(PersonLegalEntityLink.person)
            )
            .filter(Business.id.in_(business_ids), Business.deleted_at.is_(None))
            .all()
        )

    def list_all(self, status: Optional[str] = None) -> list[Business]:
        """List all active businesses. No pagination — internal aggregation use only."""
        query = self.db.query(Business).filter(Business.deleted_at.is_(None))
        if status:
            query = query.filter(Business.status == status)
        return query.order_by(Business.opened_at.desc()).all()
