from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_intake import BinderIntake
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.binders.repositories.binder_intake_repository import BinderIntakeRepository
from app.binders.repositories.binder_intake_material_repository import BinderIntakeMaterialRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_service import ClientService
from app.notification.services.notification_service import NotificationService


class BinderIntakeService:
    """Handles the 'find or create' binder intake flow."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        self.intake_repo = BinderIntakeRepository(db)
        self.material_repo = BinderIntakeMaterialRepository(db)
        self.client_repo = ClientRepository(db)
        # Used to resolve a Business for NotificationService, which expects
        # (Binder, Business) — not (Binder, Client).
        self.business_repo = BusinessRepository(db)
        self.notification_service = NotificationService(db)

    def receive(
        self,
        client_id: int,
        binder_number: str,
        period_start: date,
        received_at: date,
        received_by: int,
        notes: Optional[str] = None,
        materials: Optional[list[dict]] = None,
    ) -> tuple[Binder, BinderIntake, bool]:
        """
        Find active binder by number or create new one, then record the intake.

        materials: list of dicts with keys:
            material_type (str), business_id (int|None),
            annual_report_id (int|None), description (str|None)

        Returns (binder, intake, is_new_binder).
        """
        client = ClientService(self.db).get_client_or_raise(client_id)

        existing = self.binder_repo.get_active_by_number(binder_number)

        if existing:
            if existing.client_id != client_id:
                raise ConflictError(
                    f"הקלסר {binder_number} שייך ללקוח אחר",
                    "BINDER.CLIENT_MISMATCH",
                )
            binder = existing
            is_new_binder = False
        else:
            binder = self.binder_repo.create(
                client_id=client_id,
                binder_number=binder_number,
                period_start=period_start,
                created_by=received_by,
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

        for mat in (materials or []):
            self.material_repo.create(
                intake_id=intake.id,
                material_type=mat["material_type"],
                business_id=mat.get("business_id"),
                annual_report_id=mat.get("annual_report_id"),
                description=mat.get("description"),
            )

        if is_new_binder:
            # NotificationService.notify_binder_received expects (Binder, Business).
            # Fetch the first active business for this client.
            businesses = self.business_repo.list_by_client(client_id)
            if businesses:
                self.notification_service.notify_binder_received(binder, businesses[0])

        return binder, intake, is_new_binder