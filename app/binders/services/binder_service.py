import logging
from datetime import date
from typing import Optional

from app.utils.time_utils import utcnow

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
from app.binders.models.binder_intake_material import BinderIntakeMaterial
from app.binders.repositories.binder_intake_material_repository import BinderIntakeMaterialRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
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
        self.client_record_repo = ClientRecordRepository(db)
        self.material_repo = BinderIntakeMaterialRepository(db)
        self.notification_service = NotificationService(db)
        self.intake_service = BinderIntakeService(db)

    def receive_binder(
        self,
        client_record_id: int,
        received_at: date,
        received_by: int,
        open_new_binder: bool = False,
        notes: Optional[str] = None,
        materials: Optional[list[dict]] = None,
    ) -> tuple[Binder, BinderIntake, bool]:
        """Receive material into existing binder or create new one."""
        return self.intake_service.receive(
            client_record_id=client_record_id,
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
            ready_for_pickup_at=utcnow(),
        )

        self.status_log_repo.append(
            binder_id=binder_id,
            old_status=old_status,
            new_status=BinderStatus.READY_FOR_PICKUP.value,
            changed_by=user_id,
            notes=BINDER_MARKED_READY,
        )

        if binder.client_record_id:
            self.notification_service.notify_ready_for_pickup(updated, binder.client_record_id)

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
        """Compatibility helper for callers that still fetch raw binder entities."""
        return self.binder_repo.get_by_id(binder_id)

    def mark_ready_bulk(
        self,
        client_record_id: int,
        until_period_year: int,
        until_period_month: int,
        user_id: int,
    ) -> list[Binder]:
        """
        Mark all eligible binders for a client as READY_FOR_PICKUP.

        Eligibility:
        - binder belongs to client_record_id
        - binder status is IN_OFFICE or CLOSED_IN_OFFICE
        - binder has at least one material row with structured period
        - latest material period is <= the requested cutoff
        """
        cutoff = (until_period_year, until_period_month)
        updated: list[Binder] = []

        client_record_id = ClientRecordRepository(self.db).get_by_id(client_record_id).id
        for binder in self.binder_repo.list_by_client_record(client_record_id):
            if binder.status not in {
                BinderStatus.IN_OFFICE,
                BinderStatus.CLOSED_IN_OFFICE,
            }:
                continue
            latest_material = self.material_repo.get_last_by_binder(binder.id)
            if not self._material_period_lte_cutoff(latest_material, cutoff):
                continue
            updated.append(self.mark_ready_for_pickup(binder.id, user_id=user_id))

        return updated

    def delete_binder(self, binder_id: int, actor_id: int) -> bool:
        """Soft-delete a binder. Returns False if not found."""
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            return False
        return self.binder_repo.soft_delete(binder_id, deleted_by=actor_id)

    def list_active_binders(
        self,
        client_record_id: Optional[int] = None,
        status: Optional[str] = None,
        sort_by: str = "period_start",
        sort_dir: str = "desc",
    ) -> list[Binder]:
        """Compatibility helper for callers that still use the old service method."""
        return self.binder_repo.list_active(
            client_record_id=client_record_id,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    @staticmethod
    def _material_period_lte_cutoff(
        material: Optional[BinderIntakeMaterial],
        cutoff: tuple[int, int],
    ) -> bool:
        if not material or material.period_year is None or material.period_month_end is None:
            return False
        return (material.period_year, material.period_month_end) <= cutoff
