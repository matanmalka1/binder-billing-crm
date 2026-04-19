from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository


class AuthorityContactService:
    """Authority contact management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.contact_repo = AuthorityContactRepository(db)

    def _get_client_or_raise(self, client_id: int) -> None:
        repo = ClientRepository(self.db)
        if not repo.get_by_id(client_id):
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")

    def _get_client_record_id(self, client_id: int) -> int:
        return ClientRecordRepository(self.db).get_by_client_id(client_id).id

    def add_contact(
        self,
        client_id: int,
        contact_type: str,
        name: str,
        office: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AuthorityContact:
        """Add new authority contact for client."""
        self._get_client_or_raise(client_id)
        contact_type_enum = contact_type if isinstance(contact_type, ContactType) else ContactType(contact_type)

        return self.contact_repo.create(
            client_id=client_id,
            client_record_id=self._get_client_record_id(client_id),
            contact_type=contact_type_enum,
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
        if "contact_type" in fields:
            ct = fields["contact_type"]
            fields["contact_type"] = ct if isinstance(ct, ContactType) else ContactType(ct)

        updated = self.contact_repo.update(contact_id, **fields)
        if not updated:
            raise NotFoundError(f"איש קשר {contact_id} לא נמצא", "AUTHORITY_CONTACT.NOT_FOUND")
        return updated

    def list_client_contacts(
        self,
        client_id: int,
        contact_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuthorityContact], int]:
        """List contacts for client with pagination."""
        contact_type_enum: Optional[ContactType] = ContactType(contact_type) if contact_type else None

        client_record_id = ClientRecordRepository(self.db).get_by_client_id(client_id).id
        items = self.contact_repo.list_by_client_record(
            client_record_id, contact_type_enum, page=page, page_size=page_size
        )
        total = self.contact_repo.count_by_client_record(client_record_id, contact_type_enum)
        return items, total

    def delete_contact(self, contact_id: int, actor_id: int) -> None:
        """Soft-delete contact."""
        success = self.contact_repo.delete(contact_id, deleted_by=actor_id)
        if not success:
            raise NotFoundError(f"איש קשר {contact_id} לא נמצא", "AUTHORITY_CONTACT.NOT_FOUND")

    def get_contact(self, contact_id: int) -> AuthorityContact:
        """Get contact by ID."""
        contact = self.contact_repo.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"איש קשר {contact_id} לא נמצא", "AUTHORITY_CONTACT.NOT_FOUND")
        return contact
