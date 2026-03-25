import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_intake import BinderIntake
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.binders.repositories.binder_intake_repository import BinderIntakeRepository
from app.binders.repositories.binder_intake_material_repository import BinderIntakeMaterialRepository
from app.businesses.models.business import BusinessStatus
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_service import ClientService
from app.notification.services.notification_service import NotificationService
from app.binders.services.binder_helpers import parse_period_to_date

_log = logging.getLogger(__name__)


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
        period_start: date,
        received_at: date,
        received_by: int,
        open_new_binder: bool = False,
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
        ClientService(self.db).get_client_or_raise(client_id)

        businesses = self.business_repo.list_by_client(client_id)
        has_active = any(b.status == BusinessStatus.ACTIVE for b in businesses)
        if businesses and not has_active:
            raise AppError(
                "לא ניתן לקלוט קלסר ללקוח מוקפא או סגור",
                "BINDER.CLIENT_LOCKED",
            )

        existing = self.binder_repo.get_active_by_client(client_id)

        if existing and open_new_binder:
            existing.period_end = self._resolve_closing_period(existing.id, received_at)
            existing.is_full = True
            self.db.flush()
            existing = None

        if existing:
            binder = existing
            is_new_binder = False
        else:
            seq = self.binder_repo.count_all_by_client(client_id) + 1
            binder_number = f"{client_id}/{seq}"
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
                notes="קלסר התקבל",
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
            if businesses:
                self.notification_service.notify_binder_received(binder, businesses[0])
            else:
                _log.warning(
                    "notify_binder_received skipped: client %s has no businesses (binder %s)",
                    client_id, binder.id,
                )

        return binder, intake, is_new_binder

    def _resolve_closing_period(self, binder_id: int, fallback: date) -> date:
        """Derive period_end from the last material's description period string."""
        last_mat = self.material_repo.get_last_by_binder(binder_id)
        if not last_mat or not last_mat.description:
            return fallback
        return parse_period_to_date(last_mat.description) or fallback