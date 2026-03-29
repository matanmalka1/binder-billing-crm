from datetime import date
from typing import Optional

from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow

from app.common.repositories import BaseRepository
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus


def advance_payment_status_text_expr():
    """
    Normalize enum-backed status columns to lowercase text.

    SQLite stores enums as strings, but PostgreSQL keeps a native enum type.
    Casting avoids `lower(enum_type)` errors on PostgreSQL while preserving the
    case-insensitive matching used for legacy SQLite fixtures.
    """
    return func.lower(cast(AdvancePayment.status, String))


class AdvancePaymentRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(
        self,
        business_id: int,
        period: str,
        period_months_count: int,
        due_date: date,
        expected_amount=None,
        paid_amount=None,
        payment_method=None,
        annual_report_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        payment = AdvancePayment(
            business_id=business_id,
            period=period,
            period_months_count=period_months_count,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            payment_method=payment_method,
            annual_report_id=annual_report_id,
            notes=notes,
            status=AdvancePaymentStatus.PENDING,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_by_id(self, payment_id: int) -> Optional[AdvancePayment]:
        return (
            self.db.query(AdvancePayment)
            .filter(AdvancePayment.id == payment_id, AdvancePayment.deleted_at.is_(None))
            .first()
        )

    def get_by_id_for_business(self, payment_id: int, business_id: int) -> Optional[AdvancePayment]:
        return (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.id == payment_id,
                AdvancePayment.business_id == business_id,
                AdvancePayment.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_business_year(
        self,
        business_id: int,
        year: int,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AdvancePayment], int]:
        """List payments for a business in a given year, filtered by period prefix."""
        query = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
            .order_by(AdvancePayment.period.asc())
        )
        if status:
            normalized = [s.value.lower() for s in status]
            query = query.filter(advance_payment_status_text_expr().in_(normalized))
        total = query.count()
        items = self._paginate(query, page, page_size)
        return items, total

    def exists_for_period(self, business_id: int, period: str) -> bool:
        """Check if a payment already exists for the given period."""
        return self.db.query(
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.period == period,
                AdvancePayment.deleted_at.is_(None),
            )
            .exists()
        ).scalar()

    def list_overview_payments(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> list[AdvancePayment]:
        query = (
            self.db.query(AdvancePayment)
            .filter(
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
        )
        if month is not None:
            month_str = f"{year}-{month:02d}"
            query = query.filter(AdvancePayment.period == month_str)
        if statuses:
            normalized = [s.value.lower() for s in statuses]
            query = query.filter(advance_payment_status_text_expr().in_(normalized))
        return query.all()

    def sum_paid_by_business_year(self, business_id: int, year: int) -> float:
        result = (
            self.db.query(func.coalesce(func.sum(AdvancePayment.paid_amount), 0))
            .filter(
                AdvancePayment.business_id == business_id,
                AdvancePayment.period.like(f"{year}-%"),
                advance_payment_status_text_expr() == AdvancePaymentStatus.PAID.value,
                AdvancePayment.deleted_at.is_(None),
            )
            .scalar()
        )
        return float(result)

    def update(self, payment: AdvancePayment, **fields) -> AdvancePayment:
        return self._update_entity(payment, touch_updated_at=True, **fields)

    def soft_delete(self, payment_id: int, deleted_by: int) -> bool:
        payment = self.get_by_id(payment_id)
        if not payment:
            return False
        payment.deleted_at = utcnow()
        payment.deleted_by = deleted_by
        self.db.commit()
        return True

    def get_collections_aggregates(self, year: int, month=None) -> list:
        """Per-business aggregates for the collections report."""
        from sqlalchemy import case, func
        from app.businesses.models.business import Business
        from app.clients.models.client import Client

        query = (
            self.db.query(
                AdvancePayment.business_id,
                Business.client_id,
                Business.business_name,
                Client.full_name.label("client_name"),
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label("total_expected"),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label("total_paid"),
                func.coalesce(
                    func.sum(
                        case(
                            (advance_payment_status_text_expr() == AdvancePaymentStatus.OVERDUE.value, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("overdue_count"),
            )
            .join(Business, Business.id == AdvancePayment.business_id)
            .join(Client, Client.id == Business.client_id)
            .filter(
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
                Business.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
        )
        if month is not None:
            query = query.filter(AdvancePayment.period == f"{year}-{month:02d}")
        return query.group_by(
            AdvancePayment.business_id,
            Business.client_id,
            Business.business_name,
            Client.full_name,
        ).all()
