import json
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.audit.constants import ACTION_CREATED, ACTION_DELETED, ACTION_RESTORED, ACTION_UPDATED, ENTITY_BUSINESS
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.businesses.models.business import Business, BusinessStatus, BusinessType
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lifecycle_service import BusinessLifecycleService
from app.businesses.services.business_lookup import get_business_or_raise as _get_or_raise
from app.businesses.services.business_bulk_service import BusinessBulkService
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.users.models.user import UserRole


class BusinessService:
    """Business management — CRUD and lifecycle logic."""

    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self.client_repo = ClientRepository(db)
        self._bulk = BusinessBulkService(db)
        self._lifecycle = BusinessLifecycleService(db)
        self._audit = EntityAuditLogRepository(db)

    _SOLE_TRADER_TYPES = {BusinessType.OSEK_PATUR, BusinessType.OSEK_MURSHE}

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

        parsed_type = BusinessType(business_type)
        if parsed_type in self._SOLE_TRADER_TYPES:
            if self.business_repo.has_conflicting_sole_trader(client_id, parsed_type):
                raise ConflictError(
                    "לקוח זה רשום בסטטוס עוסק שונה — לא ניתן לשלב עוסק פטור ועוסק מורשה",
                    "BUSINESS.SOLE_TRADER_CONFLICT",
                )

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
            business = self.business_repo.create(
                client_id=client_id, business_type=business_type, opened_at=opened_at,
                business_name=business_name, notes=notes, tax_id_number=tax_id_number,
                created_by=actor_id,
            )
        except IntegrityError:
            raise ConflictError(
                f"שגיאת כפילות ביצירת עסק ללקוח {client_id}", "BUSINESS.CONFLICT",
            )

        if actor_id:
            self._audit.append(
                entity_type=ENTITY_BUSINESS,
                entity_id=business.id,
                performed_by=actor_id,
                action=ACTION_CREATED,
                new_value=json.dumps({"business_type": business_type, "client_id": client_id}),
            )
        return business

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

    def update_business(self, business_id: int, user_role: UserRole, actor_id: Optional[int] = None, **fields) -> Business:
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

        new_type = BusinessType(fields["business_type"]) if "business_type" in fields else None
        if new_type in self._SOLE_TRADER_TYPES:
            if self.business_repo.has_conflicting_sole_trader_excluding(business.client_id, new_type, business_id):
                raise ConflictError(
                    "לקוח זה רשום בסטטוס עוסק שונה — לא ניתן לשלב עוסק פטור ועוסק מורשה",
                    "BUSINESS.SOLE_TRADER_CONFLICT",
                )

        old_snapshot = {k: getattr(business, k, None) for k in fields if hasattr(business, k)}
        updated = self.business_repo.update(business_id, **fields)
        new_snapshot = {k: getattr(updated, k, None) for k in fields if hasattr(updated, k)}

        def _serialize(d):
            return {k: v.value if hasattr(v, "value") else str(v) if v is not None else None for k, v in d.items()}

        if actor_id:
            self._audit.append(
                entity_type=ENTITY_BUSINESS,
                entity_id=business_id,
                performed_by=actor_id,
                action=ACTION_UPDATED,
                old_value=json.dumps(_serialize(old_snapshot)),
                new_value=json.dumps(_serialize(new_snapshot)),
            )
        return updated

    # ─── Delete / Restore (delegated) ────────────────────────────────────────

    def delete_business(self, business_id: int, actor_id: int) -> None:
        self._lifecycle.delete_business(business_id, actor_id)

    def restore_business(self, business_id: int, actor_id: int, actor_role: UserRole) -> Business:
        return self._lifecycle.restore_business(business_id, actor_id, actor_role)
