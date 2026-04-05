from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.businesses.models.business import Business, BusinessStatus
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lookup import get_business_or_raise as _get_or_raise
from app.businesses.services.business_bulk_service import BusinessBulkService
from app.clients.repositories.client_repository import ClientRepository
from app.users.models.user import UserRole


class BusinessService:
    """Business management — CRUD and lifecycle logic."""

    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self.client_repo = ClientRepository(db)
        self._bulk = BusinessBulkService(db)

    # ─── Create ───────────────────────────────────────────────────────────────

    def create_business(
        self,
        client_id: int,
        business_type: str,
        opened_at: date,
        business_name: Optional[str] = None,
        notes: Optional[str] = None,
        tax_id_number: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> Business:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")

        if self.business_repo.all_non_deleted_are_closed(client_id):
            raise AppError(
                "כל העסקים של לקוח זה סגורים — לא ניתן להוסיף עסק חדש ללא אישור מפורש",
                "BUSINESS.CLIENT_ALL_CLOSED",
                status_code=409,
            )

        if business_name:
            for b in self.business_repo.list_by_client(client_id, page=1, page_size=10_000):
                if b.business_name and b.business_name.strip().lower() == business_name.strip().lower():
                    raise ConflictError(
                        f"עסק בשם '{business_name}' כבר קיים ללקוח זה",
                        "BUSINESS.NAME_CONFLICT",
                    )

        try:
            return self.business_repo.create(
                client_id=client_id, business_type=business_type, opened_at=opened_at,
                business_name=business_name, notes=notes, tax_id_number=tax_id_number,
                created_by=actor_id,
            )
        except IntegrityError:
            raise ConflictError(
                f"שגיאת כפילות ביצירת עסק ללקוח {client_id}", "BUSINESS.CONFLICT",
            )

    # ─── Read ─────────────────────────────────────────────────────────────────

    def get_business(self, business_id: int) -> Optional[Business]:
        return self.business_repo.get_by_id(business_id)

    def get_business_or_raise(self, business_id: int) -> Business:
        return _get_or_raise(self.db, business_id)

    def list_businesses_for_client(
        self, client_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Business], int]:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        items = self.business_repo.list_by_client(client_id, page=page, page_size=page_size)
        total = self.business_repo.count_by_client(client_id)
        return items, total

    def list_businesses(self, **kwargs) -> tuple[list[Business], int]:
        """Delegate to BusinessBulkService for signal-aware paginated listing."""
        return self._bulk.list_businesses(**kwargs)

    # ─── Update ───────────────────────────────────────────────────────────────

    def update_business(self, business_id: int, user_role: UserRole, **fields) -> Business:
        """Update business fields. FROZEN/CLOSED status requires ADVISOR role."""
        business = self.business_repo.get_by_id(business_id)
        if not business:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")

        if "status" in fields and fields["status"] is not None:
            try:
                fields["status"] = BusinessStatus(fields["status"])
            except ValueError:
                raise AppError(f"סטטוס לא חוקי: {fields['status']}", "BUSINESS.INVALID_STATUS", status_code=400)

        if "status" in fields and fields["status"] in (BusinessStatus.FROZEN, BusinessStatus.CLOSED):
            if user_role != UserRole.ADVISOR:
                raise ForbiddenError("רק יועצים יכולים להקפיא או לסגור עסקים", "BUSINESS.FORBIDDEN")

        if "status" in fields and fields["status"] == BusinessStatus.CLOSED:
            fields.setdefault("closed_at", date.today())

        if "status" in fields and fields["status"] == BusinessStatus.ACTIVE:
            fields["closed_at"] = None

        return self.business_repo.update(business_id, **fields)

    # ─── Delete / Restore ─────────────────────────────────────────────────────

    def delete_business(self, business_id: int, actor_id: int) -> None:
        if not self.business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        self.business_repo.soft_delete(business_id, deleted_by=actor_id)

    def restore_business(self, business_id: int, actor_id: int, actor_role: UserRole) -> Business:
        if actor_role != UserRole.ADVISOR:
            raise ForbiddenError("רק יועצים יכולים לשחזר עסקים", "BUSINESS.FORBIDDEN")
        business = self.business_repo.get_by_id_including_deleted(business_id)
        if not business:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        if business.deleted_at is None:
            raise ConflictError("עסק זה אינו מחוק", "BUSINESS.NOT_DELETED")
        restored = self.business_repo.restore(business_id, restored_by=actor_id)
        if not restored:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        return restored

    # ─── Bulk ─────────────────────────────────────────────────────────────────

    def bulk_update_status(
        self,
        business_ids: list[int],
        action: str,
        actor_id: int,
        actor_role: UserRole = UserRole.ADVISOR,
    ) -> tuple[list[int], list[dict]]:
        return self._bulk.bulk_update_status(
            business_ids=business_ids, action=action,
            actor_id=actor_id, actor_role=actor_role,
            update_fn=self.update_business,
        )
