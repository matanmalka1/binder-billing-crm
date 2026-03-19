from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.binders.models.binder_intake import BinderIntake
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.binders.services import binder_helpers
from app.binders.services.binder_list_service import BinderListService
from app.binders.services.binder_intake_service import BinderIntakeService
from app.notification.services.notification_service import NotificationService


class BinderService(BinderListService):
    """Binder lifecycle management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        self.business_repo = BusinessRepository(db)
        self.notification_service = NotificationService(db)
        self.intake_service = BinderIntakeService(db)

    def receive_binder(
        self,
        business_id: int,
        binder_number: str,
        binder_type: BinderType,
        received_at: date,
        received_by: int,
        notes: Optional[str] = None,
    ) -> tuple[Binder, BinderIntake, bool]:
        """Receive material into existing binder or create new one."""
        return self.intake_service.receive(
            business_id=business_id,
            binder_number=binder_number,
            binder_type=binder_type,
            received_at=received_at,
            received_by=received_by,
            notes=notes,
        )

    def mark_ready_for_pickup(self, binder_id: int, user_id: int) -> Binder:
        """Mark binder as ready for pickup."""
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise NotFoundError(f"הקלסר {binder_id} לא נמצא", "BINDER.NOT_FOUND")

        binder_helpers.validate_ready_transition(binder)

        old_status = binder.status.value
        updated = self.binder_repo.update_status(
            binder_id,
            BinderStatus.READY_FOR_PICKUP,
            binder=binder,
        )

        self.status_log_repo.append(
            binder_id=binder_id,
            old_status=old_status,
            new_status=BinderStatus.READY_FOR_PICKUP.value,
            changed_by=user_id,
            notes="סומן כמוכן לאיסוף",
        )

        business = self.business_repo.get_by_id(binder.business_id)
        if business:
            self.notification_service.notify_ready_for_pickup(updated, business)

        return updated

    def return_binder(
        self, binder_id: int, pickup_person_name: str, returned_by: int
    ) -> Binder:
        """Return binder to client."""
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise NotFoundError(f"הקלסר {binder_id} לא נמצא", "BINDER.NOT_FOUND")

        binder_helpers.validate_return_transition(binder, pickup_person_name)

        old_status = binder.status.value
        returned_at = date.today()

        updated = self.binder_repo.update_status(
            binder_id,
            BinderStatus.RETURNED,
            binder=binder,
            returned_at=returned_at,
            returned_by=returned_by,
            pickup_person_name=pickup_person_name.strip(),
        )

        self.status_log_repo.append(
            binder_id=binder_id,
            old_status=old_status,
            new_status=BinderStatus.RETURNED.value,
            changed_by=returned_by,
            notes=f"נאסף על ידי {pickup_person_name}",
        )

        return updated

    def get_binder(self, binder_id: int) -> Optional[Binder]:
        """Get binder by ID."""
        return self.binder_repo.get_by_id(binder_id)

    def delete_binder(self, binder_id: int, actor_id: int) -> bool:
        """Soft-delete a binder. Returns False if not found."""
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            return False
        return self.binder_repo.soft_delete(binder_id, deleted_by=actor_id)

    def list_active_binders(
        self,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        sort_by: str = "received_at",
        sort_dir: str = "desc",
    ) -> list[Binder]:
        """List active binders with optional filters."""
        return self.binder_repo.list_active(
            business_id=business_id,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
