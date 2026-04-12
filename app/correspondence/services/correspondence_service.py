from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
from app.correspondence.repositories.correspondence_repository import CorrespondenceRepository
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.businesses.repositories.business_repository import BusinessRepository

_NOT_FOUND = "CORRESPONDENCE.NOT_FOUND"
_FORBIDDEN_CONTACT = "CORRESPONDENCE.FORBIDDEN_CONTACT"


class CorrespondenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CorrespondenceRepository(db)
        self.contact_repo = AuthorityContactRepository(db)
        self.business_repo = BusinessRepository(db)

    def _resolve_client_id(self, business_id: int) -> int:
        """Fetch the client_id from the business. Raises if business not found."""
        business = self.business_repo.get_by_id(business_id)
        if not business or business.deleted_at is not None:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "CORRESPONDENCE.BUSINESS_NOT_FOUND")
        return business.client_id

    def _assert_contact_belongs_to_client(self, contact_id: int, client_id: int) -> None:
        """
        authority_contacts belong to a CLIENT (not a business).
        Validate against client_id — not business_id.
        """
        contact = self.contact_repo.get_by_id(contact_id)
        if not contact or contact.client_id != client_id:
            raise ForbiddenError(
                f"איש קשר {contact_id} אינו שייך ללקוח {client_id}",
                _FORBIDDEN_CONTACT,
            )

    def _get_entry_or_raise(self, entry_id: int, client_id: int) -> Correspondence:
        """Fetch entry and verify it belongs to the given client."""
        entry = self.repo.get_by_id(entry_id)
        if not entry or entry.client_id != client_id:
            raise NotFoundError(
                f"התכתבות {entry_id} לא נמצאה עבור לקוח {client_id}",
                _NOT_FOUND,
            )
        return entry

    # ── Write operations ──────────────────────────────────────────────────────

    def add_entry(
        self,
        business_id: int,                        # UI entry point — always via business
        correspondence_type: CorrespondenceType,
        subject: str,
        occurred_at: datetime,
        created_by: int,
        contact_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Correspondence:
        # Derive client_id from business — the legal entity is always the anchor
        client_id = self._resolve_client_id(business_id)

        if contact_id is not None:
            self._assert_contact_belongs_to_client(contact_id, client_id)

        return self.repo.create(
            client_id=client_id,
            business_id=business_id,
            correspondence_type=correspondence_type,
            subject=subject,
            occurred_at=occurred_at,
            created_by=created_by,
            contact_id=contact_id,
            notes=notes,
        )

    def get_entry(self, entry_id: int, business_id: int) -> Correspondence:
        client_id = self._resolve_client_id(business_id)
        return self._get_entry_or_raise(entry_id, client_id)

    def update_entry(self, entry_id: int, business_id: int, **fields) -> Correspondence:
        client_id = self._resolve_client_id(business_id)
        entry = self._get_entry_or_raise(entry_id, client_id)

        contact_id = fields.get("contact_id", entry.contact_id)
        if contact_id is not None:
            self._assert_contact_belongs_to_client(contact_id, client_id)

        updated = self.repo.update(entry_id, **fields)
        if not updated:
            raise NotFoundError(
                f"התכתבות {entry_id} לא נמצאה עבור לקוח {client_id}",
                _NOT_FOUND,
            )
        return updated

    def delete_entry(self, entry_id: int, business_id: int, actor_id: int) -> None:
        client_id = self._resolve_client_id(business_id)
        self._get_entry_or_raise(entry_id, client_id)
        self.repo.soft_delete(entry_id, deleted_by=actor_id)

    # ── Read operations ───────────────────────────────────────────────────────

    def list_business_entries(
        self,
        business_id: int,
        *,
        page: int,
        page_size: int,
        correspondence_type: Optional[CorrespondenceType] = None,
        contact_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sort_dir: str = "desc",
    ) -> tuple[list[Correspondence], int]:
        client_id = self._resolve_client_id(business_id)
        return self.repo.list_paginated(
            client_id=client_id,
            business_id=business_id,
            page=page,
            page_size=page_size,
            correspondence_type=correspondence_type,
            contact_id=contact_id,
            from_date=from_date,
            to_date=to_date,
            sort_dir=sort_dir,
        )

    def list_client_entries(
        self,
        client_id: int,
        *,
        page: int,
        page_size: int,
        correspondence_type: Optional[CorrespondenceType] = None,
        contact_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sort_dir: str = "desc",
    ) -> tuple[list[Correspondence], int]:
        """All correspondence for a client regardless of which business."""
        return self.repo.list_paginated(
            client_id=client_id,
            page=page,
            page_size=page_size,
            correspondence_type=correspondence_type,
            contact_id=contact_id,
            from_date=from_date,
            to_date=to_date,
            sort_dir=sort_dir,
        )