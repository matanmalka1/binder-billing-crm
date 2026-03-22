from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.businesses.models.business import Business, BusinessStatus
from app.utils.time_utils import utcnow


class BusinessRepository(BaseRepository):
    """Data access layer for Business entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        client_id: int,
        business_type: str,
        opened_at: date,
        business_name: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Business:
        """Create a new business under a client."""
        business = Business(
            client_id=client_id,
            business_name=business_name,
            business_type=business_type,
            opened_at=opened_at,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(business)
        self.db.commit()
        self.db.refresh(business)
        return business

    def get_by_id(self, business_id: int) -> Optional[Business]:
        """Retrieve business by ID (excludes soft-deleted)."""
        return (
            self.db.query(Business)
            .filter(
                Business.id == business_id,
                Business.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_id_including_deleted(self, business_id: int) -> Optional[Business]:
        """Retrieve business by ID regardless of deletion status."""
        return (
            self.db.query(Business)
            .filter(Business.id == business_id)
            .first()
        )

    def list_by_client(self, client_id: int) -> list[Business]:
        """List all active businesses for a client."""
        return (
            self.db.query(Business)
            .filter(
                Business.client_id == client_id,
                Business.deleted_at.is_(None),
            )
            .order_by(Business.opened_at.asc())
            .all()
        )

    def list_by_client_including_deleted(self, client_id: int) -> list[Business]:
        """List all businesses for a client including soft-deleted."""
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
        """List active businesses with optional filters.

        Signal-based filtering is intentionally excluded — it is computed
        in the service layer (SignalsService) and cannot be pushed to SQL.
        """
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

        query = query.order_by(Business.opened_at.desc())
        return self._paginate(query, page, page_size)

    def count(
        self,
        status: Optional[str] = None,
        business_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count active businesses with optional filters."""
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

        return query.count()

    def list_all(self, status: Optional[str] = None) -> list[Business]:
        """List all active businesses (optionally filtered by status)."""
        query = self.db.query(Business).filter(Business.deleted_at.is_(None))
        if status:
            query = query.filter(Business.status == status)
        return query.order_by(Business.opened_at.desc()).all()

    def list_by_ids(self, business_ids: list[int]) -> list[Business]:
        """Batch fetch businesses by IDs."""
        if not business_ids:
            return []
        return (
            self.db.query(Business)
            .filter(
                Business.id.in_(business_ids),
                Business.deleted_at.is_(None),
            )
            .all()
        )

    def soft_delete(self, business_id: int, deleted_by: int) -> bool:
        """Soft-delete a business."""
        business = self.db.query(Business).filter(Business.id == business_id).first()
        if not business:
            return False
        business.deleted_at = utcnow()
        business.deleted_by = deleted_by
        self.db.commit()
        return True

    def restore(self, business_id: int, restored_by: int) -> Optional[Business]:
        """Restore a soft-deleted business."""
        business = self.db.query(Business).filter(Business.id == business_id).first()
        if not business or business.deleted_at is None:
            return None
        business.deleted_at = None
        business.deleted_by = None
        business.restored_at = utcnow()
        business.restored_by = restored_by
        business.status = BusinessStatus.ACTIVE
        self.db.commit()
        self.db.refresh(business)
        return business

    def update(self, business_id: int, **fields) -> Optional[Business]:
        """Update business fields."""
        business = self.get_by_id(business_id)
        return self._update_entity(business, **fields)

    def exists_for_client(self, client_id: int) -> bool:
        """Check if a client has at least one active business."""
        return (
            self.db.query(Business)
            .filter(
                Business.client_id == client_id,
                Business.deleted_at.is_(None),
            )
            .first()
        ) is not None