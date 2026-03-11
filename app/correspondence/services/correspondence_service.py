from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
from app.correspondence.repositories.correspondence_repository import CorrespondenceRepository
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_lookup import get_client_or_raise


class CorrespondenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CorrespondenceRepository(db)
        self.client_repo = ClientRepository(db)
        self.contact_repo = AuthorityContactRepository(db)

    def add_entry(
        self,
        client_id: int,
        correspondence_type: CorrespondenceType,
        subject: str,
        occurred_at: datetime,
        created_by: int,
        contact_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Correspondence:
        get_client_or_raise(self.db, client_id)

        if contact_id is not None:
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact or contact.client_id != client_id:
                raise ForbiddenError(
                    f"Contact {contact_id} does not belong to client {client_id}",
                    "CORRESPONDENCE.FORBIDDEN_CONTACT",
                )

        return self.repo.create(
            client_id=client_id,
            correspondence_type=correspondence_type,
            subject=subject,
            occurred_at=occurred_at,
            created_by=created_by,
            contact_id=contact_id,
            notes=notes,
        )

    def list_client_entries(
        self, client_id: int, *, page: int, page_size: int
    ) -> tuple[list[Correspondence], int]:
        return self.repo.list_by_client_paginated(client_id, page=page, page_size=page_size)

    def update_entry(
        self,
        entry_id: int,
        client_id: int,
        **fields,
    ) -> Correspondence:
        entry = self.repo.get_by_id(entry_id)
        if not entry or entry.client_id != client_id:
            raise NotFoundError(
                f"Correspondence {entry_id} not found for client {client_id}",
                "CORRESPONDENCE.NOT_FOUND",
            )

        contact_id = fields.get("contact_id", entry.contact_id)
        if contact_id is not None:
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact or contact.client_id != client_id:
                raise ForbiddenError(
                    f"Contact {contact_id} does not belong to client {client_id}",
                    "CORRESPONDENCE.FORBIDDEN_CONTACT",
                )

        updated = self.repo.update(entry_id, **fields)
        if not updated:
            raise NotFoundError(
                f"Correspondence {entry_id} not found for client {client_id}",
                "CORRESPONDENCE.NOT_FOUND",
            )
        return updated

    def delete_entry(self, entry_id: int, client_id: int, actor_id: int) -> None:
        entry = self.repo.get_by_id(entry_id)
        if not entry or entry.client_id != client_id:
            raise NotFoundError(
                f"Correspondence {entry_id} not found for client {client_id}",
                "CORRESPONDENCE.NOT_FOUND",
            )
        self.repo.soft_delete(entry_id, deleted_by=actor_id)
