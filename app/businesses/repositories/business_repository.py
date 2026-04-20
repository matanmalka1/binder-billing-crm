from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository_read import BusinessRepositoryRead
from app.businesses.models.business import Business, BusinessStatus
from app.clients.models.client import Client
from app.clients.models.legal_entity import LegalEntity
from app.utils.time_utils import utcnow


class BusinessRepository(BusinessRepositoryRead):
    """Data access layer for Business entities (write + single-item reads)."""

    def __init__(self, db: Session):
        super().__init__(db)

    def _resolve_legal_entity_id(self, client_id: int) -> int | None:
        row = (
            self.db.query(LegalEntity.id)
            .join(
                Client,
                (Client.id_number == LegalEntity.id_number)
                & (Client.id_number_type == LegalEntity.id_number_type),
            )
            .filter(Client.id == client_id)
            .first()
        )
        return row[0] if row else None

    # ─── Write ───────────────────────────────────────────────────────────────

    def create(
        self,
        client_id: int,
        opened_at: date,
        business_name: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Business:
        legal_entity_id = self._resolve_legal_entity_id(client_id)
        business = Business(
            legal_entity_id=legal_entity_id,
            business_name=business_name,
            opened_at=opened_at,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(business)
        self.db.flush()
        return business

    def create_for_legal_entity(
        self,
        legal_entity_id: int,
        opened_at: date,
        business_name: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Business:
        business = Business(
            legal_entity_id=legal_entity_id,
            business_name=business_name,
            opened_at=opened_at,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(business)
        self.db.flush()
        return business

    def update(self, business_id: int, **fields) -> Optional[Business]:
        business = self.get_by_id(business_id)
        return self._update_entity(business, **fields)

    def soft_delete(self, business_id: int, deleted_by: int) -> bool:
        business = self.get_by_id(business_id)
        if not business:
            return False
        business.deleted_at = utcnow()
        business.deleted_by = deleted_by
        self.db.flush()
        return True

    def restore(self, business_id: int, restored_by: int) -> Optional[Business]:
        business = self.db.query(Business).filter(Business.id == business_id).first()
        if not business or business.deleted_at is None:
            return None
        business.deleted_at = None
        business.restored_at = utcnow()
        business.restored_by = restored_by
        business.status = BusinessStatus.ACTIVE
        self.db.flush()
        return business

    # ─── Read (single) ───────────────────────────────────────────────────────

    def get_by_id(self, business_id: int) -> Optional[Business]:
        return (
            self.db.query(Business)
            .filter(Business.id == business_id, Business.deleted_at.is_(None))
            .first()
        )

    def get_by_id_including_deleted(self, business_id: int) -> Optional[Business]:
        return self.db.query(Business).filter(Business.id == business_id).first()

    def exists_for_client(self, client_id: int) -> bool:
        legal_entity_id = self._resolve_legal_entity_id(client_id)
        if legal_entity_id is None:
            return False
        return self.exists_for_legal_entity(legal_entity_id)

    def all_non_deleted_are_closed(self, client_id: int) -> bool:
        """Returns True if the client has at least one non-deleted business and all are CLOSED."""
        legal_entity_id = self._resolve_legal_entity_id(client_id)
        if legal_entity_id is None:
            return False
        return self.all_non_deleted_are_closed_for_legal_entity(legal_entity_id)

    def get_ids_by_client(self, client_id: int) -> list[int]:
        """Return all non-deleted business IDs for a client."""
        legal_entity_id = self._resolve_legal_entity_id(client_id)
        if legal_entity_id is None:
            return []
        return self.get_ids_by_legal_entity(legal_entity_id)

    def exists_for_legal_entity(self, legal_entity_id: int) -> bool:
        return (
            self.db.query(Business)
            .filter(Business.legal_entity_id == legal_entity_id, Business.deleted_at.is_(None))
            .first()
        ) is not None

    def all_non_deleted_are_closed_for_legal_entity(self, legal_entity_id: int) -> bool:
        businesses = (
            self.db.query(Business)
            .filter(Business.legal_entity_id == legal_entity_id, Business.deleted_at.is_(None))
            .all()
        )
        return bool(businesses) and all(b.status == BusinessStatus.CLOSED for b in businesses)

    def get_ids_by_legal_entity(self, legal_entity_id: int) -> list[int]:
        rows = (
            self.db.query(Business.id)
            .filter(Business.legal_entity_id == legal_entity_id, Business.deleted_at.is_(None))
            .all()
        )
        return [r[0] for r in rows]

    def has_conflicting_sole_trader(
        self,
        client_id: int,
        new_type,
        exclude_business_id: int | None = None,
    ) -> bool:
        return False
