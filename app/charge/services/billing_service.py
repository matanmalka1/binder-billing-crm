import json
from typing import Optional

from sqlalchemy.orm import Session

from app.audit.constants import (
    ACTION_CANCELED, ACTION_CREATED, ACTION_DELETED, ACTION_ISSUED, ACTION_PAID, ENTITY_CHARGE,
)
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.businesses.services.business_guards import validate_business_for_create
from app.charge.models.charge import Charge, ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.reminders.services.reminder_service import ReminderService
from app.utils.time_utils import utcnow


class BillingService:
    """Billing and charge lifecycle management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self._audit = EntityAuditLogRepository(db)

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
        charge = self.charge_repo.create(
            business_id=business_id, amount=amount, charge_type=charge_type,
            period=period, months_covered=months_covered, created_by=actor_id,
        )
        if actor_id:
            self._audit.append(
                entity_type=ENTITY_CHARGE, entity_id=charge.id, performed_by=actor_id,
                action=ACTION_CREATED,
                new_value=json.dumps({"amount": str(amount), "charge_type": charge_type}),
            )
        return charge

    def issue_charge(self, charge_id: int, actor_id: Optional[int] = None) -> Charge:
        charge = self.charge_repo.get_by_id_for_update(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        if charge.status != ChargeStatus.DRAFT:
            raise AppError(
                f"לא ניתן להנפיק חיוב עם הסטטוס {charge.status.value}", "CHARGE.INVALID_STATUS",
            )
        issued = self.charge_repo.update_status(
            charge_id, ChargeStatus.ISSUED, charge=charge,
            issued_at=utcnow(), issued_by=actor_id,
        )
        ReminderService(self.db).create_unpaid_charge_reminder(
            business_id=charge.business_id, charge_id=charge_id, days_unpaid=30,
        )
        if actor_id:
            self._audit.append(
                entity_type=ENTITY_CHARGE, entity_id=charge_id, performed_by=actor_id,
                action=ACTION_ISSUED,
                old_value=ChargeStatus.DRAFT.value, new_value=ChargeStatus.ISSUED.value,
            )
        return issued

    def mark_charge_paid(self, charge_id: int, actor_id: Optional[int] = None) -> Charge:
        charge = self.charge_repo.get_by_id_for_update(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        if charge.status != ChargeStatus.ISSUED:
            raise AppError(
                f"לא ניתן לסמן חיוב כשולם כאשר הסטטוס הוא {charge.status.value}", "CHARGE.INVALID_STATUS",
            )
        paid = self.charge_repo.update_status(
            charge_id, ChargeStatus.PAID, charge=charge,
            paid_at=utcnow(), paid_by=actor_id,
        )
        ReminderService(self.db).cancel_reminders_for_charge(charge_id)
        if actor_id:
            self._audit.append(
                entity_type=ENTITY_CHARGE, entity_id=charge_id, performed_by=actor_id,
                action=ACTION_PAID,
                old_value=ChargeStatus.ISSUED.value, new_value=ChargeStatus.PAID.value,
            )
        return paid

    def cancel_charge(self, charge_id: int, actor_id: Optional[int] = None, reason: Optional[str] = None) -> Charge:
        charge = self.charge_repo.get_by_id_for_update(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        if charge.status == ChargeStatus.PAID:
            raise AppError("לא ניתן לבטל חיוב במצב שולם", "CHARGE.INVALID_STATUS")
        if charge.status == ChargeStatus.CANCELED:
            raise ConflictError("החיוב כבר בוטל", "CHARGE.CONFLICT")
        old_status = charge.status.value
        canceled = self.charge_repo.update_status(
            charge_id, ChargeStatus.CANCELED, charge=charge,
            canceled_by=actor_id, canceled_at=utcnow(), cancellation_reason=reason,
        )
        ReminderService(self.db).cancel_reminders_for_charge(charge_id)
        if actor_id:
            self._audit.append(
                entity_type=ENTITY_CHARGE, entity_id=charge_id, performed_by=actor_id,
                action=ACTION_CANCELED,
                old_value=old_status, new_value=ChargeStatus.CANCELED.value, note=reason,
            )
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
        result = self.charge_repo.soft_delete(charge_id, deleted_by=actor_id)
        if result and actor_id:
            self._audit.append(
                entity_type=ENTITY_CHARGE, entity_id=charge_id,
                performed_by=actor_id, action=ACTION_DELETED,
            )
        return result

    def get_charge(self, charge_id: int) -> Charge:
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        return charge
