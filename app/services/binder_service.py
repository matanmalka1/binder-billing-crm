from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Binder, BinderStatus
from app.repositories import (
    BinderRepository,
    BinderStatusLogRepository,
    ClientRepository,
)


class BinderService:
    """Binder lifecycle management business logic."""

    BINDER_MAX_DAYS = 90

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        self.client_repo = ClientRepository(db)

    def receive_binder(
        self,
        client_id: int,
        binder_number: str,
        received_at: date,
        received_by: int,
        notes: Optional[str] = None,
    ) -> Binder:
        """
        Receive new binder (intake flow).
        
        Business rules:
        - Calculate expected_return_at = received_at + 90 days
        - Intake is never blocked by warnings
        - Create binder and initial status log in transaction
        """
        # Verify client exists
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Check for duplicate active binder number
        existing = self.binder_repo.get_active_by_number(binder_number)
        if existing:
            raise ValueError(f"Active binder {binder_number} already exists")

        # Calculate 90-day threshold
        expected_return_at = received_at + timedelta(days=self.BINDER_MAX_DAYS)

        # Create binder
        binder = self.binder_repo.create(
            client_id=client_id,
            binder_number=binder_number,
            received_at=received_at,
            expected_return_at=expected_return_at,
            received_by=received_by,
            notes=notes,
        )

        # Log initial status
        self.status_log_repo.append(
            binder_id=binder.id,
            old_status="null",
            new_status=BinderStatus.IN_OFFICE.value,
            changed_by=received_by,
            notes="Binder received",
        )

        return binder

    def mark_ready_for_pickup(self, binder_id: int, user_id: int) -> Binder:
        """Mark binder as ready for pickup."""
        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise ValueError(f"Binder {binder_id} not found")

        if binder.status not in [BinderStatus.IN_OFFICE, BinderStatus.OVERDUE]:
            raise ValueError(f"Cannot mark binder as ready from status {binder.status}")

        old_status = binder.status.value
        updated = self.binder_repo.update_status(
            binder_id, BinderStatus.READY_FOR_PICKUP
        )

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
        """
        Return binder to client.
        
        Business rules:
        - pickup_person_name is mandatory
        - Can only return from ready_for_pickup or overdue status
        """
        if not pickup_person_name or not pickup_person_name.strip():
            raise ValueError("pickup_person_name is required")

        binder = self.binder_repo.get_by_id(binder_id)
        if not binder:
            raise ValueError(f"Binder {binder_id} not found")

        if binder.status not in [BinderStatus.READY_FOR_PICKUP, BinderStatus.OVERDUE]:
            raise ValueError(f"Cannot return binder from status {binder.status}")

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

    def mark_overdue_binders(self, reference_date: Optional[date] = None) -> int:
        """
        Mark binders as overdue based on 90-day rule.
        
        Intended for scheduled job execution.
        """
        if reference_date is None:
            reference_date = date.today()

        count = self.binder_repo.mark_overdue_by_date(reference_date)
        return count

    def get_binder(self, binder_id: int) -> Optional[Binder]:
        """Get binder by ID."""
        return self.binder_repo.get_by_id(binder_id)

    def list_active_binders(
        self, client_id: Optional[int] = None, status: Optional[str] = None
    ) -> list[Binder]:
        """List active binders with optional filters."""
        return self.binder_repo.list_active(client_id=client_id, status=status)