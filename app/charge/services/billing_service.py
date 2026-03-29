from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.charge.models.charge import Charge, ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.businesses.services.business_guards import assert_business_allows_create
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
        """
        Create new charge in draft status.

        Raises:
            AppError: If client doesn't exist or amount is invalid
        """
        # Validate client exists and allows new work
        business = get_business_or_raise(self.db, business_id)
        assert_business_allows_create(business)

        # Validate amount
        if amount <= 0:
            raise AppError("הסכום חייב להיות חיובי", "CHARGE.AMOUNT_INVALID")

        # Create charge in draft status
        return self.charge_repo.create(
            business_id=business_id,
            amount=amount,
            charge_type=charge_type,
            period=period,
            months_covered=months_covered,
            created_by=actor_id,
        )

    def issue_charge(self, charge_id: int, actor_id: Optional[int] = None) -> Charge:
        """
        Issue a draft charge.
        
        Rules:
        - Only draft charges can be issued
        - Amount and type become immutable after issue
        
        Raises:
            AppError: If charge not found or not in draft status
        """
        charge = self.charge_repo.get_by_id(charge_id)
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
        """
        Mark an issued charge as paid.
        
        Rules:
        - Only issued charges can be marked paid
        - Paid charges are immutable
        
        Raises:
            AppError: If charge not found or not in issued status
        """
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")

        if charge.status != ChargeStatus.ISSUED:
            raise AppError(
                f"לא ניתן לסמן חיוב כשולם כאשר הסטטוס הוא {charge.status.value}",
                "CHARGE.INVALID_STATUS",
            )

        return self.charge_repo.update_status(
            charge_id,
            ChargeStatus.PAID,
            paid_at=utcnow(),
            paid_by=actor_id,
        )
    

    def cancel_charge(self, charge_id: int, actor_id: Optional[int] = None, reason: Optional[str] = None) -> Charge:
        """
        Cancel a draft or issued charge.
        
        Rules:
        - Paid charges cannot be canceled
        - Already canceled charges cannot be re-canceled
        
        Raises:
            AppError: If charge not found or in invalid status
        """
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")

        if charge.status == ChargeStatus.PAID:
            raise AppError("לא ניתן לבטל חיוב במצב שולם", "CHARGE.INVALID_STATUS")

        if charge.status == ChargeStatus.CANCELED:
            raise ConflictError("החיוב כבר בוטל", "CHARGE.CONFLICT")

        return self.charge_repo.update_status(
            charge_id,
            ChargeStatus.CANCELED,
            canceled_by=actor_id,
            canceled_at=utcnow(),
            cancellation_reason=reason,
        )

    def delete_charge(self, charge_id: int, actor_id: Optional[int] = None) -> bool:
        """
        Soft-delete a draft charge.

        Rules:
        - Only DRAFT charges can be deleted (use cancel for issued charges)

        Raises:
            AppError: If charge not found or not in draft status
        """
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")

        if charge.status != ChargeStatus.DRAFT:
            raise AppError(
                f"ניתן למחוק רק חיובים במצב טיוטה. השתמש בביטול עבור סטטוס '{charge.status.value}'",
                "CHARGE.INVALID_STATUS",
            )

        return self.charge_repo.soft_delete(charge_id, deleted_by=actor_id)

    def get_charge(self, charge_id: int) -> Charge:
        """Get charge by ID. Raises NotFoundError if not found."""
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise NotFoundError(f"החיוב {charge_id} לא נמצא", "CHARGE.NOT_FOUND")
        return charge
