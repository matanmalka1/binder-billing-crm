from typing import Optional

from sqlalchemy.orm import Session

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.clients.repositories.client_repository import ClientRepository


class AuthorityContactService:
    """Authority contact management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.contact_repo = AuthorityContactRepository(db)
        self.client_repo = ClientRepository(db)

    def add_contact(
        self,
        client_id: int,
        contact_type: ContactType,
        name: str,
        office: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AuthorityContact:
        """Add new authority contact for client."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        return self.contact_repo.create(
            client_id=client_id,
            contact_type=contact_type,
            name=name,
            office=office,
            phone=phone,
            email=email,
            notes=notes,
        )

    def update_contact(
        self,
        contact_id: int,
        **fields,
    ) -> AuthorityContact:
        """Update contact details."""
        contact = self.contact_repo.get_by_id(contact_id)
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")

        updated = self.contact_repo.update(contact_id, **fields)
        return updated

    def list_client_contacts(
        self,
        client_id: int,
        contact_type: Optional[ContactType] = None,
    ) -> list[AuthorityContact]:
        """List contacts for client."""
        return self.contact_repo.list_by_client(client_id, contact_type)

    def delete_contact(self, contact_id: int) -> None:
        """Delete contact."""
        success = self.contact_repo.delete(contact_id)
        if not success:
            raise ValueError(f"Contact {contact_id} not found")

    def get_contact(self, contact_id: int) -> Optional[AuthorityContact]:
        """Get contact by ID."""
        return self.contact_repo.get_by_id(contact_id)
