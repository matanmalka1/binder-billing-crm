from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
from app.correspondence.repositories.correspondence_repository import CorrespondenceRepository
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.clients.repositories.client_repository import ClientRepository


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
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        if contact_id is not None:
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact or contact.client_id != client_id:
                raise ValueError(
                    f"Contact {contact_id} does not belong to client {client_id}"
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

    def list_client_entries(self, client_id: int) -> list[Correspondence]:
        return self.repo.list_by_client(client_id)