from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.invoice.models.invoice import Invoice


class InvoiceRepository:
    """Data access layer for Invoice entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        charge_id: int,
        provider: str,
        external_invoice_id: str,
        issued_at: datetime,
        document_url: Optional[str] = None,
    ) -> Invoice:
        """Create new invoice reference."""
        invoice = Invoice(
            charge_id=charge_id,
            provider=provider,
            external_invoice_id=external_invoice_id,
            document_url=document_url,
            issued_at=issued_at,
        )
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Retrieve invoice by ID."""
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def get_by_charge_id(self, charge_id: int) -> Optional[Invoice]:
        """Retrieve invoice by charge ID."""
        return self.db.query(Invoice).filter(Invoice.charge_id == charge_id).first()

    def list_by_charge_ids(self, charge_ids: list[int]) -> list["Invoice"]:
        """Batch-fetch invoices for a list of charge IDs (single query)."""
        if not charge_ids:
            return []
        return self.db.query(Invoice).filter(Invoice.charge_id.in_(charge_ids)).all()

    def exists_for_charge(self, charge_id: int) -> bool:
        """Check if invoice exists for charge."""
        return (
            self.db.query(Invoice)
            .filter(Invoice.charge_id == charge_id)
            .count()
            > 0
        )
