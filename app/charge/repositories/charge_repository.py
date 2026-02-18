from typing import Optional

from sqlalchemy.orm import Session

from app.models import Charge, ChargeStatus


class ChargeRepository:
    """Data access layer for Charge entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: int,
        amount: float,
        charge_type: str,
        currency: str = "ILS",
        period: Optional[str] = None,
    ) -> Charge:
        """Create new charge in draft status."""
        charge = Charge(
            client_id=client_id,
            amount=amount,
            currency=currency,
            charge_type=charge_type,
            period=period,
            status=ChargeStatus.DRAFT,
        )
        self.db.add(charge)
        self.db.commit()
        self.db.refresh(charge)
        return charge

    def get_by_id(self, charge_id: int) -> Optional[Charge]:
        """Retrieve charge by ID."""
        return self.db.query(Charge).filter(Charge.id == charge_id).first()

    def list_charges(
        self,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Charge]:
        """List charges with optional filters and pagination."""
        query = self.db.query(Charge)

        if client_id:
            query = query.filter(Charge.client_id == client_id)

        if status:
            query = query.filter(Charge.status == status)

        offset = (page - 1) * page_size
        return query.order_by(Charge.created_at.desc()).offset(offset).limit(page_size).all()

    def count_charges(
        self,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count charges with optional filters."""
        query = self.db.query(Charge)

        if client_id:
            query = query.filter(Charge.client_id == client_id)

        if status:
            query = query.filter(Charge.status == status)

        return query.count()

    def update_status(
        self,
        charge_id: int,
        new_status: ChargeStatus,
        **additional_fields,
    ) -> Optional[Charge]:
        """Update charge status and additional fields."""
        charge = self.get_by_id(charge_id)
        if not charge:
            return None

        charge.status = new_status

        for key, value in additional_fields.items():
            if hasattr(charge, key):
                setattr(charge, key, value)

        self.db.commit()
        self.db.refresh(charge)
        return charge
