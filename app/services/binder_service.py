from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Binder, BinderStatus
from app.repositories import (
    BinderRepository,
    BinderStatusLogRepository,
    ClientRepository,
)
from app.services.binder_helpers import BinderHelpers
from app.services.notification_service import NotificationService


class BinderService:
    """Binder lifecycle management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        self.client_repo = ClientRepository(db)
        self.notification_service = NotificationService(db)

    def receive_binder(
        self,
        client_id: int,
        binder_number: str,
        received_at: date,
        received_by: int,
        notes: Optional[str] = None,
    ) -> Binder:
        """Receive new binder (intake flow)."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        existing = self.binder_repo.get_active_by_number(binder_number)
        if existing:
            raise ValueError(f"Active binder {binder_number} already exists")

        expected_return_at = BinderHelpers.calculate_expected_return(received_at)

        binder = self.binder_repo.create(
            client_id=client_id,
            binder_number=binder_number,
            received_at=received_at,
            expected_return_at=expected_return_at,
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

        # Sprint 4: Send binder received notification
        self.notification_service.notify_binder_received(binder, client)

        return binder

    def mark_ready_for_pickup(self, binder_id: int, user_id: int) -> Binder:
        """Mark binder as ready for pickup."""
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise ValueError(f"Binder {binder_id} not found")

        BinderHelpers.validate_ready_transition(binder)

        old_status = binder.status.value
        updated = self.binder_repo.update_status(binder_id, BinderStatus.READY_FOR_PICKUP)

        self.status_log_repo.append(
            binder_id=binder_id,
            old_status=old_status,
            new_status=BinderStatus.READY_FOR_PICKUP.value,
            changed_by=user_id,
        )

        return updated

    def return_binder(
        self, binder_id: int, pickup_person_name: str, returned_by: int
    ) -> Binder:
        """Return binder to client."""
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise ValueError(f"Binder {binder_id} not found")

        BinderHelpers.validate_return_transition(binder, pickup_person_name)

        old_status = binder.status.value
        returned_at = date.today()

        updated = self.binder_repo.update_status(
            binder_id,
            BinderStatus.RETURNED,
            returned_at=returned_at,
            returned_by=returned_by,
            pickup_person_name=pickup_person_name.strip(),
        )

        self.status_log_repo.append(
            binder_id=binder_id,
            old_status=old_status,
            new_status=BinderStatus.RETURNED.value,
            changed_by=returned_by,
            notes=f"Picked up by {pickup_person_name}",
        )

        return updated

    def get_binder(self, binder_id: int) -> Optional[Binder]:
        """Get binder by ID."""
        return self.binder_repo.get_by_id(binder_id)

    def list_active_binders(
        self, client_id: Optional[int] = None, status: Optional[str] = None
    ) -> list[Binder]:
        """List active binders with optional filters."""
        return self.binder_repo.list_active(client_id=client_id, status=status)
