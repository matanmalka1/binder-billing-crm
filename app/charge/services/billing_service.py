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
from app.charge.services.constants import UNPAID_CHARGE_REMINDER_DAYS
from app.charge.services.messages import (
    AMOUNT_MUST_BE_POSITIVE,
    BUSINESS_CLIENT_MISMATCH,
    CHARGE_ALREADY_CANCELED,
    CHARGE_CANNOT_CANCEL_PAID,
    CHARGE_DELETE_INVALID_STATUS,
    CHARGE_INVALID_STATUS_ISSUE,
    CHARGE_INVALID_STATUS_PAY,
    CHARGE_NOT_FOUND,
    CLIENT_NOT_FOUND,
)
from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.reminders.services.reminder_service import ReminderService
from app.utils.time_utils import utcnow


class BillingService:
    """Billing and charge lifecycle management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.client_repo = ClientRepository(db)
        self._audit = EntityAuditLogRepository(db)

    def _validate_charge_scope(self, client_id: int, business_id: Optional[int]) -> Optional[int]:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CHARGE.CLIENT_NOT_FOUND")
        if business_id is None:
            return None
        business = validate_business_for_create(self.db, business_id)
        if business.client_id != client_id:
            raise AppError(
                BUSINESS_CLIENT_MISMATCH,
                "CHARGE.BUSINESS_CLIENT_MISMATCH",
            )
        return business.id

    def create_charge(
        self,
        client_id: int,
        amount: float,
        charge_type: str,
        business_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        period: Optional[str] = None,
        months_covered: int = 1,
    ) -> Charge:
        business_id = self._validate_charge_scope(client_id, business_id)
        if amount <= 0:
            raise AppError(AMOUNT_MUST_BE_POSITIVE, "CHARGE.AMOUNT_INVALID")
        charge = self.charge_repo.create(
            client_id=client_id, business_id=business_id, amount=amount, charge_type=charge_type,
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
            raise NotFoundError(CHARGE_NOT_FOUND.format(charge_id=charge_id), "CHARGE.NOT_FOUND")
        if charge.status != ChargeStatus.DRAFT:
            raise AppError(
                CHARGE_INVALID_STATUS_ISSUE.format(status=charge.status.value), "CHARGE.INVALID_STATUS",
            )
        issued = self.charge_repo.update_status(
            charge_id, ChargeStatus.ISSUED, charge=charge,
            issued_at=utcnow(), issued_by=actor_id,
        )
        ReminderService(self.db).create_unpaid_charge_reminder(
            client_id=charge.client_id, business_id=charge.business_id, charge_id=charge_id,
            days_unpaid=UNPAID_CHARGE_REMINDER_DAYS,
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
            raise NotFoundError(CHARGE_NOT_FOUND.format(charge_id=charge_id), "CHARGE.NOT_FOUND")
        if charge.status != ChargeStatus.ISSUED:
            raise AppError(
                CHARGE_INVALID_STATUS_PAY.format(status=charge.status.value), "CHARGE.INVALID_STATUS",
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
            raise NotFoundError(CHARGE_NOT_FOUND.format(charge_id=charge_id), "CHARGE.NOT_FOUND")
        if charge.status == ChargeStatus.PAID:
            raise AppError(CHARGE_CANNOT_CANCEL_PAID, "CHARGE.INVALID_STATUS")
        if charge.status == ChargeStatus.CANCELED:
            raise ConflictError(CHARGE_ALREADY_CANCELED, "CHARGE.CONFLICT")
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
            raise NotFoundError(CHARGE_NOT_FOUND.format(charge_id=charge_id), "CHARGE.NOT_FOUND")
        if charge.status not in (ChargeStatus.DRAFT, ChargeStatus.CANCELED):
            raise AppError(
                CHARGE_DELETE_INVALID_STATUS.format(status=charge.status.value),
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
            raise NotFoundError(CHARGE_NOT_FOUND.format(charge_id=charge_id), "CHARGE.NOT_FOUND")
        return charge
