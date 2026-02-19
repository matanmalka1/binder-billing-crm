from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.authority_contact.models.authority_contact import AuthorityContact, ContactType


class AuthorityContactRepository(BaseRepository):
    """Data access layer for AuthorityContact entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        client_id: int,
        contact_type: ContactType,
        name: str,
        office: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AuthorityContact:
        """Create new authority contact."""
        contact = AuthorityContact(
            client_id=client_id,
            contact_type=contact_type,
            name=name,
            office=office,
            phone=phone,
            email=email,
            notes=notes,
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def get_by_id(self, contact_id: int) -> Optional[AuthorityContact]:
        """Retrieve contact by ID."""
        return (
            self.db.query(AuthorityContact).filter(AuthorityContact.id == contact_id).first()
        )

    def list_by_client(
        self,
        client_id: int,
        contact_type: Optional[ContactType] = None,
    ) -> list[AuthorityContact]:
        """List contacts for a client."""
        query = self.db.query(AuthorityContact).filter(
            AuthorityContact.client_id == client_id
        )

        if contact_type:
            query = query.filter(AuthorityContact.contact_type == contact_type)

        return query.order_by(AuthorityContact.created_at.desc()).all()

    def update(self, contact_id: int, **fields) -> Optional[AuthorityContact]:
        """Update contact fields."""
        contact = self.get_by_id(contact_id)
        return self._update_entity(contact, **fields)

    def delete(self, contact_id: int) -> bool:
        """Delete contact."""
        contact = self.get_by_id(contact_id)
        if not contact:
            return False

        self.db.delete(contact)
        self.db.commit()
        return True
