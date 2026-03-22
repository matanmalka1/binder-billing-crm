from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
from app.correspondence.repositories.correspondence_repository import CorrespondenceRepository
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.businesses.services.business_guards import assert_business_allows_create

_NOT_FOUND = "CORRESPONDENCE.NOT_FOUND"
_FORBIDDEN_CONTACT = "CORRESPONDENCE.FORBIDDEN_CONTACT"


class CorrespondenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CorrespondenceRepository(db)
        self.contact_repo = AuthorityContactRepository(db)

    def _assert_contact_belongs_to_business(self, contact_id: int, business_id: int) -> None:
        contact = self.contact_repo.get_by_id(contact_id)
        if not contact or contact.business_id != business_id:
            raise ForbiddenError(
                f"איש קשר {contact_id} אינו שייך ללקוח {business_id}",
                _FORBIDDEN_CONTACT,
            )

    def add_entry(
        self,
        business_id: int,
        correspondence_type: CorrespondenceType,
        subject: str,
        occurred_at: datetime,
        created_by: int,
        contact_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Correspondence:
        business = get_business_or_raise(self.db, business_id)
        assert_business_allows_create(business)

        if contact_id is not None:
            self._assert_contact_belongs_to_business(contact_id, business_id)

        return self.repo.create(
            business_id=business_id,
            correspondence_type=correspondence_type,
            subject=subject,
            occurred_at=occurred_at,
            created_by=created_by,
            contact_id=contact_id,
            notes=notes,
        )

    def get_entry(self, entry_id: int, business_id: int) -> Correspondence:
        entry = self.repo.get_by_id(entry_id)
        if not entry or entry.business_id != business_id:
            raise NotFoundError(
                f"התכתבות {entry_id} לא נמצאה עבור לקוח {business_id}",
                _NOT_FOUND,
            )
        return entry

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
        return self.repo.list_by_business_paginated(
            business_id,
            page=page,
            page_size=page_size,
            correspondence_type=correspondence_type,
            contact_id=contact_id,
            from_date=from_date,
            to_date=to_date,
            sort_dir=sort_dir,
        )

    def update_entry(
        self,
        entry_id: int,
        business_id: int,
        **fields,
    ) -> Correspondence:
        entry = self.repo.get_by_id(entry_id)
        if not entry or entry.business_id != business_id:
            raise NotFoundError(
                f"התכתבות {entry_id} לא נמצאה עבור לקוח {business_id}",
                _NOT_FOUND,
            )

        contact_id = fields.get("contact_id", entry.contact_id)
        if contact_id is not None:
            self._assert_contact_belongs_to_business(contact_id, business_id)

        updated = self.repo.update(entry_id, **fields)
        if not updated:
            raise NotFoundError(
                f"התכתבות {entry_id} לא נמצאה עבור לקוח {business_id}",
                _NOT_FOUND,
            )
        return updated

    def delete_entry(self, entry_id: int, business_id: int, actor_id: int) -> None:
        entry = self.repo.get_by_id(entry_id)
        if not entry or entry.business_id != business_id:
            raise NotFoundError(
                f"התכתבות {entry_id} לא נמצאה עבור לקוח {business_id}",
                _NOT_FOUND,
            )
        self.repo.soft_delete(entry_id, deleted_by=actor_id)
