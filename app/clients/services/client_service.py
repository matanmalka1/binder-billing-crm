from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError
from app.clients.models.client import Client
from app.clients.repositories.client_repository import ClientRepository
from app.utils.time_utils import utcnow


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
        # בדיקת לקוח פעיל קיים
        active_clients = self.client_repo.get_active_by_id_number(id_number)
        if active_clients:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {id_number} כבר קיים במערכת",
                "CLIENT.CONFLICT",
                extra={"client_id": active_clients[0].id},
            )

        # בדיקת לקוחות מחוקים
        deleted_clients = self.client_repo.get_deleted_by_id_number(id_number)
        if deleted_clients:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {id_number} קיים במערכת אך נמחק",
                "CLIENT.DELETED_EXISTS",
                extra={"deleted_clients": [c.id for c in deleted_clients]},
            )

        try:
            return self.client_repo.create(
                full_name=full_name,
                id_number=id_number,
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

    def get_client(self, client_id: int) -> Optional[Client]:
        """Get client by ID."""
        return self.client_repo.get_by_id(client_id)

    def get_client_or_raise(self, client_id: int) -> Client:
        """Get client by ID or raise NotFoundError."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        return client

    def update_client(self, client_id: int, **fields) -> Optional[Client]:
        """Update client identity fields (name, phone, email, address)."""
        # מסיר שדות עסקיים אם הועברו בטעות
        business_fields = {
            "client_type", "status", "primary_binder_number",
            "opened_at", "closed_at",
        }
        fields = {k: v for k, v in fields.items() if k not in business_fields}
        return self.client_repo.update(client_id, **fields)

    def delete_client(self, client_id: int, actor_id: int) -> bool:
        """
        Soft-delete a client.
        שים לב: מחיקת לקוח לא מוחקת את העסקים שלו — יש למחוק אותם בנפרד דרך BusinessService.
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            return False
        return self.client_repo.soft_delete(client_id, deleted_by=actor_id)

    def restore_client(self, client_id: int, actor_id: int) -> Client:
        """Restore a soft-deleted client."""
        client = self.client_repo.get_by_id_including_deleted(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        if client.deleted_at is None:
            raise ConflictError("לקוח זה אינו מחוק", "CLIENT.NOT_DELETED")

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