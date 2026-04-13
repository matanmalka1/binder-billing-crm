import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.binders.models.binder import Binder, BinderStatus
from app.binders.services.messages import (
    BINDER_MARKED_READY,
    BINDER_NOT_FOUND,
    BINDER_PICKED_UP_BY,
    BINDER_READY_REVERTED,
)
from app.binders.models.binder_intake import BinderIntake
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_repository import ClientRepository
from app.binders.services import binder_helpers

_log = logging.getLogger(__name__)
from app.binders.services.binder_list_service import BinderListService
from app.binders.services.binder_intake_service import BinderIntakeService
from app.notification.services.notification_service import NotificationService


class BinderService(BinderListService):
    """Binder lifecycle management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        # Binders belong to clients, but notifications use Business objects.
        # BusinessRepository is used here to look up the primary business
        # for the client so NotificationService receives the correct type.
        self.client_repo = ClientRepository(db)
        self.business_repo = BusinessRepository(db)
        self.notification_service = NotificationService(db)
        self.intake_service = BinderIntakeService(db)

    def receive_binder(
        self,
        client_id: int,
        period_start: date,
        received_at: date,
        received_by: int,
        open_new_binder: bool = False,
        notes: Optional[str] = None,
        materials: Optional[list[dict]] = None,
    ) -> tuple[Binder, BinderIntake, bool]:
        """Receive material into existing binder or create new one."""
        return self.intake_service.receive(
            client_id=client_id,
            period_start=period_start,
            open_new_binder=open_new_binder,
            received_at=received_at,
            received_by=received_by,
            notes=notes,
            materials=materials,
        )

    def mark_ready_for_pickup(self, binder_id: int, user_id: int) -> Binder:
        """Mark binder as ready for pickup."""
        binder = self.binder_repo.get_by_id_for_update(binder_id)
        if not binder:
            raise NotFoundError(BINDER_NOT_FOUND.format(binder_id=binder_id), "BINDER.NOT_FOUND")

        binder_helpers.validate_ready_transition(binder)

        old_status = binder.status.value
        updated = self.binder_repo.update_status(
            binder_id, BinderStatus.READY_FOR_PICKUP, binder=binder,
        )

        self.status_log_repo.append(
            binder_id=binder_id,
            old_status=old_status,
            new_status=BinderStatus.READY_FOR_PICKUP.value,
            changed_by=user_id,
            notes=BINDER_MARKED_READY,
        )

        businesses = self.business_repo.list_by_client(binder.client_id)
        if businesses:
            # TODO: Binders are client-scoped, not business-scoped (all businesses share one binder).
            # When a client has multiple businesses, we default to the first one for the notification.
            # This may reference the wrong business name in the notification message.
            # Proper fix requires either storing the primary business on the client, or letting the
            # caller pass a business_id hint. Tracked in TODO.md.
            self.notification_service.notify_ready_for_pickup(updated, businesses[0])
        else:
            _log.warning(
                "notify_ready_for_pickup skipped: client %s has no businesses (binder %s)",
                binder.client_id, binder_id,
            )

        return updated

    def return_binder(
        self,
        binder_id: int,
        pickup_person_name: str,
        returned_by: int,
        returned_at: Optional[date] = None,
    ) -> Binder:
        """Return binder to client."""
        binder = self.binder_repo.get_by_id_for_update(binder_id)
        if not binder:
            raise NotFoundError(BINDER_NOT_FOUND.format(binder_id=binder_id), "BINDER.NOT_FOUND")

        binder_helpers.validate_return_transition(binder, pickup_person_name)

        old_status = binder.status.value
        effective_returned_at = returned_at or date.today()

        extra = {} if binder.period_end is not None else {"period_end": effective_returned_at}
        updated = self.binder_repo.update_status(
            binder_id,
            BinderStatus.RETURNED,
            binder=binder,
            returned_at=effective_returned_at,
            pickup_person_name=pickup_person_name.strip(),
            **extra,
        )

        self.status_log_repo.append(
            binder_id=binder_id,
            old_status=old_status,
            new_status=BinderStatus.RETURNED.value,
            changed_by=returned_by,
            notes=BINDER_PICKED_UP_BY.format(pickup_person_name=pickup_person_name),
        )

        return updated

    def revert_ready(self, binder_id: int, user_id: int) -> Binder:
        """Revert binder from READY_FOR_PICKUP back to IN_OFFICE."""
        binder = self.binder_repo.get_by_id_for_update(binder_id)
        if not binder:
            raise NotFoundError(BINDER_NOT_FOUND.format(binder_id=binder_id), "BINDER.NOT_FOUND")

        binder_helpers.validate_revert_ready_transition(binder)

        old_status = binder.status.value
        updated = self.binder_repo.update_status(binder_id, BinderStatus.IN_OFFICE, binder=binder)

        self.status_log_repo.append(
            binder_id=binder_id,
            old_status=old_status,
            new_status=BinderStatus.IN_OFFICE.value,
            changed_by=user_id,
            notes=BINDER_READY_REVERTED,
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
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        sort_by: str = "period_start",
        sort_dir: str = "desc",
    ) -> list[Binder]:
        """List active binders with optional filters."""
        return self.binder_repo.list_active(
            client_id=client_id,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )