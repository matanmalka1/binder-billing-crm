from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.businesses.services.business_lookup import get_business_or_raise


class AuthorityContactService:
    """Authority contact management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.contact_repo = AuthorityContactRepository(db)

    def add_contact(
        self,
        business_id: int,
        contact_type: str,
        name: str,
        office: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AuthorityContact:
        """Add new authority contact for business."""
        get_business_or_raise(self.db, business_id)
        contact_type_enum = ContactType(contact_type)

        return self.contact_repo.create(
            business_id=business_id,
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
            fields["contact_type"] = ContactType(fields["contact_type"])

        updated = self.contact_repo.update(contact_id, **fields)
        if not updated:
            raise NotFoundError(f"איש קשר {contact_id} לא נמצא", "AUTHORITY_CONTACT.NOT_FOUND")
        return updated

    def list_business_contacts(
        self,
        business_id: int,
        contact_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuthorityContact], int]:
        """List contacts for business with pagination."""
        contact_type_enum: Optional[ContactType] = ContactType(contact_type) if contact_type else None

        items = self.contact_repo.list_by_business(
            business_id, contact_type_enum, page=page, page_size=page_size
        )
        total = self.contact_repo.count_by_business(business_id, contact_type_enum)
        return items, total

    def delete_contact(self, contact_id: int, actor_id: int) -> None:
        """Soft-delete contact."""
        success = self.contact_repo.delete(contact_id, deleted_by=actor_id)
        if not success:
            raise NotFoundError(f"איש קשר {contact_id} לא נמצא", "AUTHORITY_CONTACT.NOT_FOUND")

    def get_contact(self, contact_id: int) -> Optional[AuthorityContact]:
        """Get contact by ID."""
        return self.contact_repo.get_by_id(contact_id)
