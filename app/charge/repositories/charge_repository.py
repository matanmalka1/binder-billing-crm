from datetime import date, timedelta
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.charge.models.charge import Charge, ChargeStatus
from app.utils.time_utils import utcnow


class ChargeRepository(BaseRepository):
    """Data access layer for Charge entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        client_record_id: int,
        amount: float,
        charge_type: str,
        business_id: Optional[int] = None,
        period: Optional[str] = None,
        months_covered: int = 1,
        created_by: Optional[int] = None,
    ) -> Charge:
        """Create new charge in draft status."""
        charge = Charge(
            client_record_id=client_record_id,
            business_id=business_id,
            amount=amount,
            charge_type=charge_type,
            period=period,
            months_covered=months_covered,
            status=ChargeStatus.DRAFT,
            created_by=created_by,
        )
        self.db.add(charge)
        self.db.flush()
        return charge

    def get_by_id(self, charge_id: int) -> Optional[Charge]:
        """Retrieve charge by ID (excludes soft-deleted)."""
        return (
            self.db.query(Charge)
            .filter(Charge.id == charge_id, Charge.deleted_at.is_(None))
            .first()
        )

    def get_by_id_for_update(self, charge_id: int) -> Optional[Charge]:
        """Retrieve charge with a row-level lock for status transitions."""
        return self._locked_first(
            self.db.query(Charge).filter(Charge.id == charge_id, Charge.deleted_at.is_(None))
        )

    def _base_filter(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
        business_ids: Optional[list[int]] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
    ):
        """
        Shared filter builder for list and count queries.

        Filter priority:
        - client_record_id → always applied when provided (primary anchor)
        - business_id → narrows to a single business within the client
        - business_ids → narrows to a set of businesses (used by bulk/overview queries)
          Note: business_id and business_ids are mutually exclusive; business_id wins.
        """
        query = self.db.query(Charge).filter(Charge.deleted_at.is_(None))

        if client_record_id is not None:
            query = query.filter(Charge.client_record_id == client_record_id)

        if business_id is not None:
            query = query.filter(Charge.business_id == business_id)
        elif business_ids is not None:
            if not business_ids:
                # Explicit empty list → caller wants zero results
                return None
            query = query.filter(Charge.business_id.in_(business_ids))

        if status:
            query = query.filter(Charge.status == status)
        if charge_type:
            query = query.filter(Charge.charge_type == charge_type)

        return query

    def list_charges(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
        business_ids: Optional[list[int]] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Charge]:
        """List charges with optional filters and pagination."""
        query = self._base_filter(client_record_id, business_id, business_ids, status, charge_type)
        if query is None:
            return []
        return self._paginate(query.order_by(Charge.created_at.desc()), page, page_size)

    def list_charges_by_client_record(
        self,
        client_record_id: int,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Charge]:
        return self.list_charges(
            client_record_id=client_record_id,
            business_id=business_id,
            status=status,
            charge_type=charge_type,
            page=page,
            page_size=page_size,
        )

    def count_charges(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
        business_ids: Optional[list[int]] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
    ) -> int:
        """Count charges with optional filters."""
        query = self._base_filter(client_record_id, business_id, business_ids, status, charge_type)
        if query is None:
            return 0
        return query.count()

    def count_charges_by_client_record(
        self,
        client_record_id: int,
        business_id: Optional[int] = None,
        status: Optional[str] = None,
        charge_type: Optional[str] = None,
    ) -> int:
        return self.count_charges(
            client_record_id=client_record_id,
            business_id=business_id,
            status=status,
            charge_type=charge_type,
        )

    def update_status(
        self,
        charge_id: int,
        new_status: ChargeStatus,
        charge: Optional[Charge] = None,
        **additional_fields,
    ) -> Optional[Charge]:
        """Update charge status and additional fields.

        Pass a pre-fetched (optionally locked) ``charge`` entity to avoid a second
        SELECT and to keep the lock acquired by get_by_id_for_update() in scope.
        """
        entity = charge or self.get_by_id(charge_id)
        return self._update_status(entity, new_status, **additional_fields)

    def stats_by_status(
        self,
        client_record_id: Optional[int] = None,
        charge_type: Optional[str] = None,
    ) -> dict[str, dict]:
        """Return count and total amount per status, ignoring status filter."""
        from decimal import Decimal
        query = (
            self.db.query(Charge.status, func.count(Charge.id), func.sum(Charge.amount))
            .filter(Charge.deleted_at.is_(None))
        )
        if client_record_id is not None:
            query = query.filter(Charge.client_record_id == client_record_id)
        if charge_type:
            query = query.filter(Charge.charge_type == charge_type)
        rows = query.group_by(Charge.status).all()
        return {
            str(s.value): {"count": count, "amount": str(total or Decimal(0))}
            for s, count, total in rows
        }

    def get_aging_buckets(self, as_of_date: date) -> list:
        """Aggregate unpaid (ISSUED) charges per client into aging buckets via SQL."""
        cut_30 = as_of_date - timedelta(days=30)
        cut_60 = as_of_date - timedelta(days=60)
        cut_90 = as_of_date - timedelta(days=90)

        issued_date = func.date(Charge.issued_at)

        rows = (
            self.db.query(
                Charge.client_record_id,
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
            .group_by(Charge.client_record_id)
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
        self.db.flush()
        return True
