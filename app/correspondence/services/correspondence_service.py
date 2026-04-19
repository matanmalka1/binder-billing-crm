from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
from app.correspondence.repositories.correspondence_repository import CorrespondenceRepository
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_guards import assert_business_belongs_to_legal_entity
from app.clients.repositories.client_repository import ClientRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository

_NOT_FOUND = "CORRESPONDENCE.NOT_FOUND"
_FORBIDDEN_CONTACT = "CORRESPONDENCE.FORBIDDEN_CONTACT"


class CorrespondenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CorrespondenceRepository(db)
        self.contact_repo = AuthorityContactRepository(db)
        self.business_repo = BusinessRepository(db)
        self.client_repo = ClientRepository(db)

    def _get_client_or_raise(self, client_id: int):
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        return client

    def _assert_business_belongs_to_client(
        self, business_id: int, client_id: int, legal_entity_id: Optional[int] = None
    ) -> None:
        """Validate optional business context belongs to the same client."""
        business = self.business_repo.get_by_id(business_id)
        if not business:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        if legal_entity_id is not None:
            assert_business_belongs_to_legal_entity(business, legal_entity_id)
        elif business.client_id != client_id:
            raise NotFoundError(
                f"עסק {business_id} לא נמצא",
                "BUSINESS.NOT_FOUND",
            )

    def _get_client_record_id(self, client_id: int) -> int:
        return ClientRecordRepository(self.db).get_by_client_id(client_id).id

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
        client_id: int,
        correspondence_type: CorrespondenceType,
        subject: str,
        occurred_at: datetime,
        created_by: int,
        business_id: Optional[int] = None,
        contact_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Correspondence:
        self._get_client_or_raise(client_id)
        if business_id is not None:
            self._assert_business_belongs_to_client(business_id, client_id)

        if contact_id is not None:
            self._assert_contact_belongs_to_client(contact_id, client_id)

        return self.repo.create(
            client_id=client_id,
            client_record_id=self._get_client_record_id(client_id),
            business_id=business_id,
            correspondence_type=correspondence_type,
            subject=subject,
            occurred_at=occurred_at,
            created_by=created_by,
            contact_id=contact_id,
            notes=notes,
        )

    def get_entry(self, entry_id: int, client_id: int) -> Correspondence:
        self._get_client_or_raise(client_id)
        return self._get_entry_or_raise(entry_id, client_id)

    def update_entry(self, entry_id: int, client_id: int, **fields) -> Correspondence:
        self._get_client_or_raise(client_id)
        entry = self._get_entry_or_raise(entry_id, client_id)

        business_id = fields.get("business_id", entry.business_id)
        if business_id is not None:
            self._assert_business_belongs_to_client(business_id, client_id)

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

    def delete_entry(self, entry_id: int, client_id: int, actor_id: int) -> None:
        self._get_client_or_raise(client_id)
        self._get_entry_or_raise(entry_id, client_id)
        self.repo.soft_delete(entry_id, deleted_by=actor_id)

    def list_client_entries(
        self,
        client_id: int,
        *,
        page: int,
        page_size: int,
        business_id: Optional[int] = None,
        correspondence_type: Optional[CorrespondenceType] = None,
        contact_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sort_dir: str = "desc",
    ) -> tuple[list[Correspondence], int]:
        """All correspondence for a client, optionally filtered by business context."""
        self._get_client_or_raise(client_id)
        if business_id is not None:
            self._assert_business_belongs_to_client(business_id, client_id)
        client_record_id = ClientRecordRepository(self.db).get_by_client_id(client_id).id
        return self.repo.list_by_client_record_paginated(
            client_record_id,
            business_id=business_id,
            page=page,
            page_size=page_size,
            correspondence_type=correspondence_type,
            contact_id=contact_id,
            from_date=from_date,
            to_date=to_date,
            sort_dir=sort_dir,
        )
