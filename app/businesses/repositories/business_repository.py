from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository_read import BusinessRepositoryRead
from app.businesses.models.business import Business, BusinessStatus
from app.utils.time_utils import utcnow


class BusinessRepository(BusinessRepositoryRead):
    """Data access layer for Business entities (write + single-item reads)."""

    def __init__(self, db: Session):
        super().__init__(db)

    # ─── Write ───────────────────────────────────────────────────────────────

    def create(
        self,
        client_id: int,
        business_type: str,
        opened_at: date,
        business_name: Optional[str] = None,
        notes: Optional[str] = None,
        tax_id_number: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Business:
        business = Business(
            client_id=client_id,
            business_name=business_name,
            business_type=business_type,
            opened_at=opened_at,
            notes=notes,
            tax_id_number=tax_id_number,
            created_by=created_by,
        )
        self.db.add(business)
        self.db.commit()
        self.db.refresh(business)
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
        self.db.commit()
        return True

    def restore(self, business_id: int, restored_by: int) -> Optional[Business]:
        business = self.db.query(Business).filter(Business.id == business_id).first()
        if not business or business.deleted_at is None:
            return None
        business.deleted_at = None
        business.restored_at = utcnow()
        business.restored_by = restored_by
        business.status = BusinessStatus.ACTIVE
        self.db.commit()
        self.db.refresh(business)
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
        return (
            self.db.query(Business)
            .filter(Business.client_id == client_id, Business.deleted_at.is_(None))
            .first()
        ) is not None

    def all_non_deleted_are_closed(self, client_id: int) -> bool:
        """Returns True if the client has at least one non-deleted business and all are CLOSED."""
        businesses = (
            self.db.query(Business)
            .filter(Business.client_id == client_id, Business.deleted_at.is_(None))
            .all()
        )
        return bool(businesses) and all(b.status == BusinessStatus.CLOSED for b in businesses)

    def get_ids_by_client(self, client_id: int) -> list[int]:
        """Return all non-deleted business IDs for a client."""
        rows = (
            self.db.query(Business.id)
            .filter(Business.client_id == client_id, Business.deleted_at.is_(None))
            .all()
        )
        return [r[0] for r in rows]
