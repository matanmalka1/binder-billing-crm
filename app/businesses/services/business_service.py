from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.businesses.models.business import Business, BusinessStatus
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_repository import ClientRepository
from app.users.models.user import UserRole
from app.binders.services.signals_service import SignalsService

_HAS_SIGNALS_FETCH_LIMIT = 1000


class BusinessService:
    """Business management — all operational logic lives here."""

    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self.client_repo = ClientRepository(db)
        self.signals_service = SignalsService(db)

    # ─── Create ───────────────────────────────────────────────────────────────

    def create_business(
        self,
        client_id: int,
        business_type: str,
        opened_at: date,
        business_name: Optional[str] = None,
        notes: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> Business:
        """
        יוצר עסק חדש תחת לקוח קיים.
        לקוח יכול להחזיק מספר עסקים.
        אם business_name סופק — חייב להיות ייחודי לאותו לקוח.
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")

        # בדיקת כפילות שם עסק לאותו לקוח
        if business_name:
            existing_businesses = self.business_repo.list_by_client(client_id)
            for b in existing_businesses:
                if b.business_name and b.business_name.strip() == business_name.strip():
                    raise ConflictError(
                        f"עסק בשם '{business_name}' כבר קיים ללקוח זה",
                        "BUSINESS.NAME_CONFLICT",
                    )

        try:
            return self.business_repo.create(
                client_id=client_id,
                business_type=business_type,
                opened_at=opened_at,
                business_name=business_name,
                notes=notes,
                created_by=actor_id,
            )
        except IntegrityError:
            raise ConflictError(
                f"שגיאת כפילות ביצירת עסק ללקוח {client_id}",
                "BUSINESS.CONFLICT",
            )

    # ─── Read ─────────────────────────────────────────────────────────────────

    def get_business(self, business_id: int) -> Optional[Business]:
        return self.business_repo.get_by_id(business_id)

    def get_business_or_raise(self, business_id: int) -> Business:
        business = self.business_repo.get_by_id(business_id)
        if not business:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        return business

    def list_businesses_for_client(self, client_id: int) -> list[Business]:
        """List all active businesses for a client."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        return self.business_repo.list_by_client(client_id)

    def list_businesses(
        self,
        status: Optional[str] = None,
        business_type: Optional[str] = None,
        search: Optional[str] = None,
        has_signals: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[Business], int]:
        """List businesses with pagination and optional filters."""
        if has_signals is None:
            items = self.business_repo.list(
                status=status,
                business_type=business_type,
                search=search,
                page=page,
                page_size=page_size,
            )
            total = self.business_repo.count(
                status=status,
                business_type=business_type,
                search=search,
            )
            return items, total

        total_count = self.business_repo.count(
            status=status,
            business_type=business_type,
            search=search,
        )
        if total_count > _HAS_SIGNALS_FETCH_LIMIT:
            raise AppError(
                f"מספר העסקים ({total_count}) חורג מהמגבלה לסינון לפי איתותים "
                f"({_HAS_SIGNALS_FETCH_LIMIT}). יש להשתמש בפילטרים נוספים.",
                "BUSINESS.SIGNAL_FILTER_LIMIT",
            )

        base_businesses = self.business_repo.list(
            status=status,
            business_type=business_type,
            search=search,
            page=1,
            page_size=_HAS_SIGNALS_FETCH_LIMIT,
        )
        filtered = [
            b for b in base_businesses
            if self._business_has_operational_signals(b.id, reference_date) == has_signals
        ]
        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset: offset + page_size], total

    # ─── Update ───────────────────────────────────────────────────────────────

    def update_business(
        self,
        business_id: int,
        user_role: UserRole,
        **fields,
    ) -> Optional[Business]:
        """Update business fields. Status changes to FROZEN/CLOSED require ADVISOR role."""
        business = self.business_repo.get_by_id(business_id)
        if not business:
            return None

        if "status" in fields and fields["status"] in (
            BusinessStatus.FROZEN, BusinessStatus.CLOSED
        ):
            if user_role != UserRole.ADVISOR:
                raise ForbiddenError(
                    "רק יועצים יכולים להקפיא או לסגור עסקים",
                    "BUSINESS.FORBIDDEN",
                )

        if "status" in fields and fields["status"] == BusinessStatus.CLOSED:
            if "closed_at" not in fields:
                fields["closed_at"] = date.today()

        return self.business_repo.update(business_id, **fields)

    # ─── Delete / Restore ─────────────────────────────────────────────────────

    def delete_business(self, business_id: int, actor_id: int) -> bool:
        """Soft-delete a business."""
        business = self.business_repo.get_by_id(business_id)
        if not business:
            return False
        return self.business_repo.soft_delete(business_id, deleted_by=actor_id)

    def restore_business(
        self,
        business_id: int,
        actor_id: int,
        actor_role: UserRole,
    ) -> Business:
        """Restore a soft-deleted business. ADVISOR only."""
        if actor_role != UserRole.ADVISOR:
            raise ForbiddenError(
                "רק יועצים יכולים לשחזר עסקים",
                "BUSINESS.FORBIDDEN",
            )

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
        """Apply freeze/close/activate to multiple businesses. Never raises on partial failure."""
        action_to_status = {
            "freeze": BusinessStatus.FROZEN,
            "close": BusinessStatus.CLOSED,
            "activate": BusinessStatus.ACTIVE,
        }
        new_status = action_to_status[action]
        succeeded: list[int] = []
        failed: list[dict] = []

        for business_id in business_ids:
            try:
                result = self.update_business(
                    business_id=business_id,
                    user_role=actor_role,
                    status=new_status,
                )
                if result is None:
                    raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
                succeeded.append(business_id)
            except Exception as exc:
                failed.append({"id": business_id, "error": str(exc)})

        return succeeded, failed

    # ─── Signals ──────────────────────────────────────────────────────────────

    def _business_has_operational_signals(
        self,
        business_id: int,
        reference_date: Optional[date] = None,
    ) -> bool:
        signals = self.signals_service.compute_business_signals(
            business_id=business_id,
            reference_date=reference_date,
        )
        return bool(
            signals.get("missing_documents")
            or signals.get("unpaid_charges")
            or signals.get("binder_signals")
        )
