from typing import Optional

from sqlalchemy.orm import Session

from app.models import Charge, ChargeStatus
from app.repositories import ChargeRepository, ClientRepository
from app.utils.time import utcnow


class BillingService:
    """Billing and charge lifecycle management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.client_repo = ClientRepository(db)

    def create_charge(
        self,
        client_id: int,
        amount: float,
        charge_type: str,
        period: Optional[str] = None,
        currency: str = "ILS",
    ) -> Charge:
        """
        Create new charge in draft status.
        
        Raises:
            ValueError: If client doesn't exist or amount is invalid
        """
        # Validate client exists
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Validate amount
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Create charge in draft status
        return self.charge_repo.create(
            client_id=client_id,
            amount=amount,
            charge_type=charge_type,
            period=period,
            currency=currency,
        )

    def issue_charge(self, charge_id: int) -> Charge:
        """
        Issue a draft charge.
        
        Rules:
        - Only draft charges can be issued
        - Amount and type become immutable after issue
        
        Raises:
            ValueError: If charge not found or not in draft status
        """
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise ValueError(f"Charge {charge_id} not found")

        if charge.status != ChargeStatus.DRAFT:
            raise ValueError(f"Cannot issue charge with status {charge.status.value}")

        return self.charge_repo.update_status(
            charge_id,
            ChargeStatus.ISSUED,
            issued_at=utcnow(),
        )

    def mark_charge_paid(self, charge_id: int) -> Charge:
        """
        Mark an issued charge as paid.
        
        Rules:
        - Only issued charges can be marked paid
        - Paid charges are immutable
        
        Raises:
            ValueError: If charge not found or not in issued status
        """
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise ValueError(f"Charge {charge_id} not found")

        if charge.status != ChargeStatus.ISSUED:
            raise ValueError(
                f"Cannot mark charge as paid with status {charge.status.value}"
            )

        return self.charge_repo.update_status(
            charge_id,
            ChargeStatus.PAID,
            paid_at=utcnow(),
        )

    def cancel_charge(self, charge_id: int) -> Charge:
        """
        Cancel a draft or issued charge.
        
        Rules:
        - Paid charges cannot be canceled
        - Already canceled charges cannot be re-canceled
        
        Raises:
            ValueError: If charge not found or in invalid status
        """
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise ValueError(f"Charge {charge_id} not found")

        if charge.status == ChargeStatus.PAID:
            raise ValueError("Cannot cancel paid charge")

        if charge.status == ChargeStatus.CANCELED:
            raise ValueError("Charge already canceled")

        return self.charge_repo.update_status(charge_id, ChargeStatus.CANCELED)

    def get_charge(self, charge_id: int) -> Optional[Charge]:
        """Get charge by ID."""
        return self.charge_repo.get_by_id(charge_id)

    def list_charges(
        self,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Charge], int]:
        """List charges with pagination. Returns (items, total)."""
        items = self.charge_repo.list_charges(
            client_id=client_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        total = self.charge_repo.count_charges(client_id=client_id, status=status)
        return items, total
