from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError
from app.clients.models.client import Client, IdNumberType
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_binder_helper import create_initial_binder


class ClientService:
    """
    Client identity management.
    עסקים (Business) מנוהלים ב-BusinessService.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)

    def create_client(
        self,
        full_name: str,
        id_number: str,
        id_number_type: IdNumberType = IdNumberType.INDIVIDUAL,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address_street: Optional[str] = None,
        address_building_number: Optional[str] = None,
        address_apartment: Optional[str] = None,
        address_city: Optional[str] = None,
        address_zip_code: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> Client:
        """
        יוצר לקוח חדש (רשומת זהות בלבד).
        אם לקוח עם אותו ת.ז. כבר קיים ופעיל — זורק CLIENT.CONFLICT עם client_id.
        אם לקוח עם אותו ת.ז. קיים אך מחוק — זורק CLIENT.DELETED_EXISTS עם רשימת הרשומות.
        """
        active_clients = self.client_repo.get_active_by_id_number(id_number)
        if active_clients:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {id_number} כבר קיים במערכת",
                "CLIENT.CONFLICT",
            )

        deleted_clients = self.client_repo.get_deleted_by_id_number(id_number)
        if deleted_clients:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {id_number} קיים במערכת אך נמחק",
                "CLIENT.DELETED_EXISTS",
            )

        try:
            client = self.client_repo.create(
                full_name=full_name,
                id_number=id_number,
                id_number_type=id_number_type,
                phone=phone,
                email=email,
                address_street=address_street,
                address_building_number=address_building_number,
                address_apartment=address_apartment,
                address_city=address_city,
                address_zip_code=address_zip_code,
                created_by=actor_id,
            )
        except IntegrityError:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {id_number} כבר קיים",
                "CLIENT.CONFLICT",
            )
        create_initial_binder(self.db, client, actor_id)
        return client

    def get_client(self, client_id: int) -> Optional[Client]:
        """Get client by ID."""
        return self.client_repo.get_by_id(client_id)

    def get_client_or_raise(self, client_id: int) -> Client:
        """Get client by ID or raise NotFoundError."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        return client

    def update_client(self, client_id: int, **fields) -> Client:
        """Update client identity fields (name, phone, email, address)."""
        self.get_client_or_raise(client_id)
        return self.client_repo.update(client_id, **fields)

    def delete_client(self, client_id: int, actor_id: int) -> None:
        """
        Soft-delete a client.
        שים לב: מחיקת לקוח לא מוחקת את העסקים שלו — יש למחוק אותם בנפרד דרך BusinessService.
        """
        client = self.client_repo.get_by_id_including_deleted(client_id)
        # Preserve current API contract: deleting a missing/already-deleted client
        # returns CLIENT.NOT_FOUND.
        if not client or client.deleted_at is not None:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        self.client_repo.soft_delete(client_id, deleted_by=actor_id)

    def restore_client(self, client_id: int, actor_id: int) -> Client:
        """Restore a soft-deleted client."""
        client = self.client_repo.get_by_id_including_deleted(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        if client.deleted_at is None:
            raise ConflictError("לקוח זה אינו מחוק", "CLIENT.NOT_DELETED")

        active = self.client_repo.get_active_by_id_number(client.id_number)
        if active:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {client.id_number} כבר קיים ופעיל במערכת",
                "CLIENT.CONFLICT",
            )

        restored = self.client_repo.restore(client_id, restored_by=actor_id)
        if not restored:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        return restored

    def list_clients(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Client], int]:
        """List clients with pagination."""
        items = self.client_repo.list(search=search, page=page, page_size=page_size)
        total = self.client_repo.count(search=search)
        return items, total

    def list_all_clients(self) -> list[Client]:
        """Return all active clients."""
        return self.client_repo.list_all()

    def get_conflict_info(self, id_number: str) -> dict:
        """
        מחזיר מידע מלא על קונפליקטים לת.ז. נתונה.
        משמש את ה-router לבניית תגובת 409 מפורטת.
        """
        active = self.client_repo.get_active_by_id_number(id_number)
        deleted = self.client_repo.get_deleted_by_id_number(id_number)
        return {
            "active_clients": active,
            "deleted_clients": deleted,
        }
