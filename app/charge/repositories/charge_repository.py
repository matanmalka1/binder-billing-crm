from datetime import date, timedelta
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.common.repositories import BaseRepository
from app.charge.models.charge import Charge, ChargeStatus
from app.utils.time_utils import utcnow


class ChargeRepository(BaseRepository):
    """Data access layer for Charge entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        business_id: int,
        amount: float,
        charge_type: str,
        period: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Charge:
        """Create new charge in draft status."""
        charge = Charge(
            business_id=business_id,
            amount=amount,
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
        """Retrieve charge by ID (excludes soft-deleted)."""
        return (
            self.db.query(Charge)
            .filter(Charge.id == charge_id, Charge.deleted_at.is_(None))
            .first()
        )

    def list_charges(
        self,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Charge]:
        """List charges with optional filters and pagination."""
        query = self.db.query(Charge).filter(Charge.deleted_at.is_(None))

        if business_id:
            query = query.filter(Charge.business_id == business_id)

        if status:
            query = query.filter(Charge.status == status)

        if charge_type:
            query = query.filter(Charge.charge_type == charge_type)

        query = query.order_by(Charge.created_at.desc())
        return self._paginate(query, page, page_size)

    def count_charges(
        self,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
    ) -> int:
        """Count charges with optional filters."""
        query = self.db.query(Charge).filter(Charge.deleted_at.is_(None))

        if business_id:
            query = query.filter(Charge.business_id == business_id)

        if status:
            query = query.filter(Charge.status == status)

        if charge_type:
            query = query.filter(Charge.charge_type == charge_type)

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

    def get_aging_buckets(self, as_of_date: date) -> list:
        """Aggregate unpaid (ISSUED) charges per client into aging buckets via SQL."""
        cut_30 = as_of_date - timedelta(days=30)
        cut_60 = as_of_date - timedelta(days=60)
        cut_90 = as_of_date - timedelta(days=90)

        issued_date = func.date(Charge.issued_at)

        rows = (
            self.db.query(
                Charge.business_id,
                func.sum(
                    case((issued_date >= str(cut_30), Charge.amount), else_=0)
                ).label("current"),
                func.sum(
                    case(
                        (issued_date.between(str(cut_60), str(cut_30 - timedelta(days=1))), Charge.amount),
                        else_=0,
                    )
                ).label("days_30"),
                func.sum(
                    case(
                        (issued_date.between(str(cut_90), str(cut_60 - timedelta(days=1))), Charge.amount),
                        else_=0,
                    )
                ).label("days_60"),
                func.sum(
                    case((issued_date < str(cut_90), Charge.amount), else_=0)
                ).label("days_90_plus"),
                func.sum(Charge.amount).label("total"),
                func.min(Charge.issued_at).label("oldest_issued_at"),
            )
            .filter(
                Charge.status == ChargeStatus.ISSUED.value,
                Charge.issued_at.isnot(None),
                Charge.deleted_at.is_(None),
            )
            .group_by(Charge.business_id)
            .all()
        )
        return rows

    def soft_delete(self, charge_id: int, deleted_by: int) -> bool:
        """Soft-delete a charge by setting deleted_at."""
        charge = self.get_by_id(charge_id)
        if not charge:
            return False
        charge.deleted_at = utcnow()
        charge.deleted_by = deleted_by
        self.db.commit()
        return True
