import json
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.audit.constants import ACTION_CREATED, ENTITY_BUSINESS
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.businesses.constants import _SOLE_TRADER_TYPES
from app.businesses.models.business import Business, BusinessType  # BusinessType used in create_business
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lifecycle_service import BusinessLifecycleService
from app.businesses.services.business_update_service import BusinessUpdateService
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.obligation_orchestrator import generate_client_obligations
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.users.models.user import UserRole


class BusinessService:
    """Business management — CRUD and lifecycle logic."""

    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self.client_repo = ClientRepository(db)
        self._lifecycle = BusinessLifecycleService(db)
        self._update = BusinessUpdateService(db)
        self._audit = EntityAuditLogRepository(db)

    # ─── Create ───────────────────────────────────────────────────────────────

    def create_business(
        self,
        client_id: int,
        business_type: str,
        opened_at: Optional[date] = None,
        business_name: Optional[str] = None,
        notes: Optional[str] = None,
        tax_id_number: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> Business:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")

        effective_opened_at = opened_at or getattr(client, "business_start_date", None) or date.today()

        parsed_type = BusinessType(business_type)
        if parsed_type in _SOLE_TRADER_TYPES:
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
                client_id=client_id, business_type=business_type, opened_at=effective_opened_at,
                business_name=business_name, notes=notes, tax_id_number=tax_id_number,
                created_by=actor_id,
            )
        except IntegrityError:
            raise ConflictError(
                f"שגיאת כפילות ביצירת עסק ללקוח {client_id}", "BUSINESS.CONFLICT",
            )

        generate_client_obligations(
            self.db, client_id, actor_id=actor_id,
            entity_type=getattr(client, "entity_type", None),
            best_effort=False,
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
        business = self.business_repo.get_by_id(business_id)
        from app.core.exceptions import NotFoundError
        if not business:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        return business

    def list_businesses_for_client(
        self, client_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Business], int]:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        items = self.business_repo.list_by_client(client_id, page=page, page_size=page_size)
        total = self.business_repo.count_by_client(client_id)
        return items, total

    # ─── Update ───────────────────────────────────────────────────────────────

    def update_business(
        self, business_id: int, client_id: int, user_role: UserRole,
        actor_id: Optional[int] = None, **fields
    ) -> Business:
        return self._update.update_business(
            business_id, client_id=client_id, user_role=user_role, actor_id=actor_id, **fields
        )

    # ─── Delete / Restore (delegated) ────────────────────────────────────────

    def delete_business(self, business_id: int, actor_id: int) -> None:
        self._lifecycle.delete_business(business_id, actor_id)

    def restore_business(self, business_id: int, actor_id: int, actor_role: UserRole) -> Business:
        return self._lifecycle.restore_business(business_id, actor_id, actor_role)
