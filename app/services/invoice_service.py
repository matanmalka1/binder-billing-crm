from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ChargeStatus, Invoice
from app.repositories import ChargeRepository, InvoiceRepository


class InvoiceService:
    """Invoice reference management business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.charge_repo = ChargeRepository(db)

    def attach_invoice_to_charge(
        self,
        charge_id: int,
        provider: str,
        external_invoice_id: str,
        issued_at: datetime,
        document_url: Optional[str] = None,
    ) -> Invoice:
        """
        Attach external invoice reference to a charge.
        
        Rules:
        - Charge must exist and be issued
        - Each charge can have at most one invoice
        - Invoice metadata is immutable once stored
        
        Raises:
            ValueError: If charge not found, not issued, or already has invoice
        """
        # Validate charge exists
        charge = self.charge_repo.get_by_id(charge_id)
        if not charge:
            raise ValueError(f"Charge {charge_id} not found")

        # Validate charge is issued
        if charge.status != ChargeStatus.ISSUED:
            raise ValueError(
                f"Cannot attach invoice to charge with status {charge.status.value}"
            )

        # Validate no existing invoice
        if self.invoice_repo.exists_for_charge(charge_id):
            raise ValueError(f"Charge {charge_id} already has an invoice")

        # Create invoice reference
        return self.invoice_repo.create(
            charge_id=charge_id,
            provider=provider,
            external_invoice_id=external_invoice_id,
            issued_at=issued_at,
            document_url=document_url,
        )

    def get_invoice_by_charge(self, charge_id: int) -> Optional[Invoice]:
        """Get invoice for a charge (if exists)."""
        return self.invoice_repo.get_by_charge_id(charge_id)

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID."""
        return self.invoice_repo.get_by_id(invoice_id)
