from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.charge.models.charge import Charge, ChargeStatus


class ChargeRepository(BaseRepository):
    """Data access layer for Charge entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        client_id: int,
        amount: float,
        charge_type: str,
        currency: str = "ILS",
        period: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Charge:
        """Create new charge in draft status."""
        charge = Charge(
            client_id=client_id,
            amount=amount,
            currency=currency,
            charge_type=charge_type,
            period=period,
            status=ChargeStatus.DRAFT,
            created_by=created_by,
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

        query = query.order_by(Charge.created_at.desc())
        return self._paginate(query, page, page_size)

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
        return self._update_status(charge, new_status, **additional_fields)
