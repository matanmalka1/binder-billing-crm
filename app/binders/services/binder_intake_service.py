from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.binders.models.binder_intake import BinderIntake
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.binders.repositories.binder_intake_repository import BinderIntakeRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.clients.services.client_lookup import assert_business_allows_create
from app.notification.services.notification_service import NotificationService


class BinderIntakeService:
    """Handles the 'find or create' binder intake flow."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        self.intake_repo = BinderIntakeRepository(db)
        self.notification_service = NotificationService(db)

    def receive(
        self,
        business_id: int,
        binder_number: str,
        binder_type: BinderType,
        received_at: date,
        received_by: int,
        notes: Optional[str] = None,
    ) -> tuple[Binder, BinderIntake, bool]:
        """
        Find active binder or create new one, then record the intake.
        Returns (binder, intake, is_new_binder).
        """
        business = get_business_or_raise(self.db, business_id)
        assert_business_allows_create(business)

        existing = self.binder_repo.get_active_by_number(binder_number)

        if existing:
            if existing.business_id != business_id:
                raise ConflictError(
                    f"הקלסר {binder_number} שייך לעסק אחר",
                    "BINDER.BUSINESS_MISMATCH",
                )
            binder = existing
            is_new_binder = False
        else:
            binder = self.binder_repo.create(
                business_id=business_id,
                binder_number=binder_number,
                binder_type=binder_type,
                received_at=received_at,
                received_by=received_by,
                notes=notes,
            )
            self.status_log_repo.append(
                binder_id=binder.id,
                old_status="null",
                new_status=BinderStatus.IN_OFFICE.value,
                changed_by=received_by,
                notes="Binder received",
            )
            is_new_binder = True

        intake = self.intake_repo.create(
            binder_id=binder.id,
            received_at=received_at,
            received_by=received_by,
            notes=notes,
        )

        if is_new_binder:
            self.notification_service.notify_binder_received(binder, business)

        return binder, intake, is_new_binder
