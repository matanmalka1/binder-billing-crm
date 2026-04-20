from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_handover import BinderHandover
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.binders.repositories.binder_handover_repository import BinderHandoverRepository
from app.binders.services.messages import BINDER_HANDOVER_INVALID_BINDERS, BINDER_PICKED_UP_BY
from app.clients.guards.client_record_guards import assert_client_record_is_active
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import NotFoundError


class BinderHandoverService:
    """Grouped binder handover: return multiple binders to a client in one event."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        self.handover_repo = BinderHandoverRepository(db)

    def create_handover(
        self,
        client_record_id: int,
        binder_ids: list[int],
        received_by_name: str,
        handed_over_at: date,
        until_period_year: int,
        until_period_month: int,
        actor_id: int,
        notes: Optional[str] = None,
    ) -> BinderHandover:
        """
        Return multiple binders to a client in a single grouped handover event.

        Validates:
        - All binders belong to client_record_id
        - All binders are in READY_FOR_PICKUP status

        Transitions each binder to RETURNED and creates a BinderHandover record.
        """
        binders = self._load_and_validate_binders(client_record_id, binder_ids)

        for binder in binders:
            old_status = binder.status.value
            binder.status = BinderStatus.RETURNED
            binder.returned_at = handed_over_at
            binder.pickup_person_name = received_by_name
            self.db.flush()

            self.status_log_repo.append(
                binder_id=binder.id,
                old_status=old_status,
                new_status=BinderStatus.RETURNED.value,
                changed_by=actor_id,
                notes=BINDER_PICKED_UP_BY.format(pickup_person_name=received_by_name),
            )

        handover = self.handover_repo.create(
            client_record_id=client_record_id,
            received_by_name=received_by_name,
            handed_over_at=handed_over_at,
            until_period_year=until_period_year,
            until_period_month=until_period_month,
            binder_ids=binder_ids,
            created_by=actor_id,
            notes=notes,
        )

        return handover

    def _load_and_validate_binders(
        self, client_record_id: int, binder_ids: list[int]
    ) -> list[Binder]:
        binders = []
        for bid in binder_ids:
            binder = self.binder_repo.get_by_id_for_update(bid)
            if not binder or binder.client_record_id != client_record_id:
                raise AppError(BINDER_HANDOVER_INVALID_BINDERS, "BINDER.HANDOVER_INVALID")
            if binder.status != BinderStatus.READY_FOR_PICKUP:
                raise AppError(BINDER_HANDOVER_INVALID_BINDERS, "BINDER.HANDOVER_INVALID")
            binders.append(binder)
        return binders
