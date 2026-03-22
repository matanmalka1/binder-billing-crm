from typing import Optional, Union

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.charge.models.charge import Charge, ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.charge.schemas.charge import ChargeListResponse, ChargeResponse, ChargeResponseSecretary
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_lookup import get_business_or_raise
from app.businesses.services.business_guards import assert_business_allows_create
from app.users.models.user import UserRole
from app.utils.time_utils import utcnow
from app.reminders.services.reminder_service import ReminderService


class BillingService:
    """Billing and charge lifecycle management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.business_repo = BusinessRepository(db)

    def create_charge(
        self,
        business_id: int,
        amount: float,
        charge_type: str,
        actor_id: Optional[int] = None,
        period: Optional[str] = None,
        currency: str = "ILS",
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
            currency=currency,
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

    def get_charge(self, charge_id: int) -> Optional[Charge]:
        """Get charge by ID."""
        return self.charge_repo.get_by_id(charge_id)

    def enrich_business_name(self, charge: Charge) -> str | None:
        """Return the business full_name for a single charge."""
        businesses = self.business_repo.list_by_ids([charge.business_id])
        return businesses[0].full_name if businesses else None

    def list_charges(
        self,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Charge], int, dict[int, str]]:
        """
        List charges with pagination.

        Returns (items, total, business_name_map) where business_name_map maps
        business_id → full_name for all charges in the page.
        """
        items = self.charge_repo.list_charges(
            business_id=business_id,
            status=status,
            charge_type=charge_type,
            page=page,
            page_size=page_size,
        )
        total = self.charge_repo.count_charges(business_id=business_id, status=status, charge_type=charge_type)

        # Batch-fetch client names for this page (single extra query)
        business_ids = list({c.business_id for c in items})
        businesses = self.business_repo.list_by_ids(business_ids)
        business_name_map: dict[int, str] = {c.id: c.full_name for c in businesses}

        return items, total, business_name_map

    def list_charges_for_role(
        self,
        user_role: UserRole,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ChargeListResponse:
        """List charges serialized and role-shaped in one call."""
        items, total, business_name_map = self.list_charges(
            business_id=business_id, status=status, charge_type=charge_type, page=page, page_size=page_size
        )
        schema = ChargeResponseSecretary if user_role == UserRole.SECRETARY else ChargeResponse

        def _enrich(charge: Charge) -> Union[ChargeResponse, ChargeResponseSecretary]:
            data = schema.model_validate(charge).model_dump()
            data["client_name"] = business_name_map.get(charge.business_id)
            return schema(**data)

        return ChargeListResponse(
            items=[_enrich(c) for c in items],
            page=page,
            page_size=page_size,
            total=total,
        )
