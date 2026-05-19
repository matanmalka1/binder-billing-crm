from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.common.repositories.base_repository import BaseRepository
from app.utils.time_utils import utcnow


class AuthorityContactRepository(BaseRepository[AuthorityContact]):
    """Data access layer for AuthorityContact entities."""

    model = AuthorityContact

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        client_record_id: int,
        contact_type: ContactType,
        name: str,
        office: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        notes: str | None = None,
    ) -> AuthorityContact:
        """Create new authority contact."""
        contact = AuthorityContact(
            client_record_id=client_record_id,
            contact_type=contact_type,
            name=name,
            office=office,
            phone=phone,
            email=email,
            notes=notes,
        )
        self.db.add(contact)
        self.db.flush()
        return contact

    def _base_where(self, client_record_id: int, contact_type: ContactType | None = None) -> list:
        conditions = [
            AuthorityContact.client_record_id == client_record_id,
            AuthorityContact.deleted_at.is_(None),
        ]
        if contact_type:
            conditions.append(AuthorityContact.contact_type == contact_type)
        return conditions

    def list_by_client_record(
        self,
        client_record_id: int,
        contact_type: ContactType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AuthorityContact]:
        stmt = (
            select(AuthorityContact)
            .where(*self._base_where(client_record_id, contact_type))
            .order_by(AuthorityContact.created_at.desc())
        )
        stmt = self.apply_pagination(stmt, page, page_size)
        return list(self.db.scalars(stmt).all())

    def count_by_client_record(
        self,
        client_record_id: int,
        contact_type: ContactType | None = None,
    ) -> int:
        return self.db.scalar(
            select(func.count(AuthorityContact.id)).where(
                *self._base_where(client_record_id, contact_type)
            )
        )

    def update(self, contact_id: int, **fields) -> AuthorityContact | None:
        """Update contact fields."""
        contact = self.get_by_id(contact_id)
        return self._update_entity(contact, touch_updated_at=True, **fields)

    def delete(
        self,
        contact_id: int,
        deleted_by: int | None = None,
        *,
        hard: bool = False,
    ) -> bool:
        """Soft-delete contact, preserving the record for audit."""
        contact = self.get_by_id(contact_id)
        if not contact:
            return False

        contact.deleted_at = utcnow()
        contact.deleted_by = deleted_by
        self.db.flush()
        return True
