from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.charge.models.charge import Charge, ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.businesses.services.business_guards import validate_business_for_create
from app.utils.time_utils import utcnow
from app.reminders.services.reminder_service import ReminderService


class BillingService:
    """Billing and charge lifecycle management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)

    def create_charge(
        self,
        business_id: int,
        amount: float,
        charge_type: str,
        actor_id: Optional[int] = None,
        period: Optional[str] = None,
        months_covered: int = 1,
    ) -> Charge:
        validate_business_for_create(self.db, business_id)
        if amount <= 0:
            raise AppError("הסכום חייב להיות חיובי", "CHARGE.AMOUNT_INVALID")
        return self.charge_repo.create(
            business_id=business_id,
            amount=amount,
            charge_type=charge_type,
            period=period,
            months_covered=months_covered,
            created_by=actor_id,
        )

    def issue_charge(self, charge_id: int, actor_id: Optional[int] = None) -> Charge:
        charge = self.charge_repo.get_by_id_for_update(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        if charge.status != ChargeStatus.DRAFT:
            raise AppError(
                f"לא ניתן להנפיק חיוב עם הסטטוס {charge.status.value}",
                "CHARGE.INVALID_STATUS",
            )
        issued = self.charge_repo.update_status(
            charge_id,
            ChargeStatus.ISSUED,
            charge=charge,
            issued_at=utcnow(),
            issued_by=actor_id,
        )
        ReminderService(self.db).create_unpaid_charge_reminder(
            business_id=charge.business_id,
            charge_id=charge_id,
            days_unpaid=30,
        )
        return issued

    def mark_charge_paid(self, charge_id: int, actor_id: Optional[int] = None) -> Charge:
        charge = self.charge_repo.get_by_id_for_update(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        if charge.status != ChargeStatus.ISSUED:
            raise AppError(
                f"לא ניתן לסמן חיוב כשולם כאשר הסטטוס הוא {charge.status.value}",
                "CHARGE.INVALID_STATUS",
            )
        paid = self.charge_repo.update_status(
            charge_id,
            ChargeStatus.PAID,
            charge=charge,
            paid_at=utcnow(),
            paid_by=actor_id,
        )
        ReminderService(self.db).cancel_reminders_for_charge(charge_id)
        return paid

    def cancel_charge(self, charge_id: int, actor_id: Optional[int] = None, reason: Optional[str] = None) -> Charge:
        charge = self.charge_repo.get_by_id_for_update(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        if charge.status == ChargeStatus.PAID:
            raise AppError("לא ניתן לבטל חיוב במצב שולם", "CHARGE.INVALID_STATUS")
        if charge.status == ChargeStatus.CANCELED:
            raise ConflictError("החיוב כבר בוטל", "CHARGE.CONFLICT")
        canceled = self.charge_repo.update_status(
            charge_id,
            ChargeStatus.CANCELED,
            charge=charge,
            canceled_by=actor_id,
            canceled_at=utcnow(),
            cancellation_reason=reason,
        )
        ReminderService(self.db).cancel_reminders_for_charge(charge_id)
        return canceled

    def delete_charge(self, charge_id: int, actor_id: Optional[int] = None) -> bool:
        """Soft-delete a DRAFT or CANCELED charge."""
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        if charge.status not in (ChargeStatus.DRAFT, ChargeStatus.CANCELED):
            raise AppError(
                f"ניתן למחוק רק חיובים במצב טיוטה או מבוטל. השתמש בביטול עבור סטטוס '{charge.status.value}'",
                "CHARGE.INVALID_STATUS",
            )
        return self.charge_repo.soft_delete(charge_id, deleted_by=actor_id)

    def get_charge(self, charge_id: int) -> Charge:
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        return charge
