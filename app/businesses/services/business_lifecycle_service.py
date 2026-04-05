"""Business delete and restore operations."""

import json

from sqlalchemy.orm import Session

from app.audit.constants import ACTION_DELETED, ACTION_RESTORED, ENTITY_BUSINESS
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.businesses.models.business import Business
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lookup import get_business_or_raise as _get_or_raise
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.users.models.user import UserRole


class BusinessLifecycleService:
    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self._audit = EntityAuditLogRepository(db)

    def delete_business(self, business_id: int, actor_id: int) -> None:
        if not self.business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        self.business_repo.soft_delete(business_id, deleted_by=actor_id)
        self._audit.append(
            entity_type=ENTITY_BUSINESS,
            entity_id=business_id,
            performed_by=actor_id,
            action=ACTION_DELETED,
        )

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
        self._audit.append(
            entity_type=ENTITY_BUSINESS,
            entity_id=business_id,
            performed_by=actor_id,
            action=ACTION_RESTORED,
        )
        return restored
