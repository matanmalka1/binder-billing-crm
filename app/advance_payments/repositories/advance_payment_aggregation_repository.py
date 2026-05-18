"""Aggregation and overview queries for AdvancePayment entities."""

from datetime import date
from typing import Optional

from sqlalchemy import Integer, String, case, cast, func, select
from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.repositories.base_repository import BaseRepository
from app.advance_payments.models.advance_payment import (
    AdvancePayment,
    AdvancePaymentStatus,
)


def advance_payment_start_month_expr():
    return cast(func.substr(AdvancePayment.period, 6, 2), Integer)


def advance_payment_matches_month_expr(month: int):
    start_month = advance_payment_start_month_expr()
    end_month = start_month + AdvancePayment.period_months_count - 1
    return (start_month <= month) & (end_month >= month)


class AdvancePaymentAggregationRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db)

    def list_overview_payments(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> list[AdvancePayment]:
        stmt = scope_to_active_clients_stmt(
            select(AdvancePayment), AdvancePayment
        ).where(
            AdvancePayment.period.like(f"{year}-%"),
            AdvancePayment.deleted_at.is_(None),
        )
        if month is not None:
            stmt = stmt.where(advance_payment_matches_month_expr(month))
        if statuses:
            stmt = stmt.where(AdvancePayment.status.in_(statuses))
        return list(self.db.scalars(stmt).all())

    def list_overview_payment_rows(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
        page: int,
        page_size: int,
        client_search: str | None = None,
        due_date: date | None = None,
        period_months_count: int | None = None,
    ) -> tuple[list[tuple[AdvancePayment, int | None, str, str | None]], int]:
        filters = [
            AdvancePayment.period.like(f"{year}-%"),
            AdvancePayment.deleted_at.is_(None),
        ]
        if month is not None:
            filters.append(advance_payment_matches_month_expr(month))
        if due_date is not None:
            filters.append(AdvancePayment.due_date == due_date)
        if period_months_count is not None:
            filters.append(AdvancePayment.period_months_count == period_months_count)
        if statuses:
            filters.append(AdvancePayment.status.in_(statuses))
        normalized_search = client_search.strip() if client_search else None
        if normalized_search:
            like = f"%{normalized_search}%"
            filters.append(
                (LegalEntity.official_name.ilike(like))
                | (LegalEntity.id_number.ilike(like))
                | (cast(ClientRecord.office_client_number, String).ilike(like))
            )

        count_stmt = (
            scope_to_active_clients_stmt(
                select(func.count(AdvancePayment.id)), AdvancePayment
            )
            .outerjoin(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .where(*filters)
        )
        total = self.db.scalar(count_stmt)

        offset = (page - 1) * page_size
        stmt = (
            scope_to_active_clients_stmt(
                select(
                    AdvancePayment,
                    ClientRecord.office_client_number,
                    func.coalesce(LegalEntity.official_name, "").label("official_name"),
                    LegalEntity.id_number,
                ),
                AdvancePayment,
            )
            .outerjoin(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .where(*filters)
            .order_by(
                func.coalesce(LegalEntity.official_name, "").asc(),
                AdvancePayment.period.asc(),
            )
            .offset(offset)
            .limit(page_size)
        )
        return list(self.db.execute(stmt).tuples().all()), int(total or 0)

    def sum_paid_by_client_year(self, client_record_id: int, year: int) -> float:
        result = self.db.scalar(
            select(func.coalesce(func.sum(AdvancePayment.paid_amount), 0)).where(
                AdvancePayment.client_record_id == client_record_id,
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.status == AdvancePaymentStatus.PAID,
                AdvancePayment.deleted_at.is_(None),
            )
        )
        return float(result)

    def get_collections_aggregates(self, year: int, month=None) -> list:
        """Per-client aggregates for the collections report."""
        today_expr = func.current_date()
        not_paid_expr = AdvancePayment.status != AdvancePaymentStatus.PAID
        stmt = scope_to_active_clients_stmt(
            select(
                AdvancePayment.client_record_id,
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label(
                    "total_expected"
                ),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label(
                    "total_paid"
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (AdvancePayment.due_date < today_expr) & not_paid_expr,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("overdue_count"),
            ),
            AdvancePayment,
        ).where(
            AdvancePayment.period.like(f"{year}-%"),
            AdvancePayment.deleted_at.is_(None),
        )
        if month is not None:
            stmt = stmt.where(advance_payment_matches_month_expr(month))
        return self.db.execute(stmt.group_by(AdvancePayment.client_record_id)).all()

    def get_annual_kpis_for_client(self, client_record_id: int, year: int) -> dict:
        today_expr = func.current_date()
        paid_expr = AdvancePayment.status == AdvancePaymentStatus.PAID
        not_paid_expr = AdvancePayment.status != AdvancePaymentStatus.PAID
        rows = self.db.execute(
            select(
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label(
                    "total_expected"
                ),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label(
                    "total_paid"
                ),
                func.count(AdvancePayment.id).label("total_count"),
                func.sum(
                    case(
                        (
                            (AdvancePayment.due_date < today_expr) & not_paid_expr,
                            1,
                        ),
                        else_=0,
                    )
                ).label("overdue_count"),
                func.sum(
                    case(
                        (paid_expr, 1),
                        else_=0,
                    )
                ).label("on_time_count"),
            ).where(
                AdvancePayment.client_record_id == client_record_id,
                AdvancePayment.period.like(f"{year}-%"),
                AdvancePayment.deleted_at.is_(None),
            )
        ).one()
        return {
            "total_expected": float(rows.total_expected),
            "total_paid": float(rows.total_paid),
            "overdue_count": int(rows.overdue_count or 0),
            "on_time_count": int(rows.on_time_count or 0),
        }

    def get_overview_kpis(
        self,
        year: int,
        month: Optional[int],
        statuses: list[AdvancePaymentStatus],
    ) -> dict:
        stmt = scope_to_active_clients_stmt(
            select(
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0),
            ),
            AdvancePayment,
        ).where(
            AdvancePayment.period.like(f"{year}-%"),
            AdvancePayment.deleted_at.is_(None),
        )
        if month is not None:
            stmt = stmt.where(advance_payment_matches_month_expr(month))
        if statuses:
            stmt = stmt.where(AdvancePayment.status.in_(statuses))
        total_expected, total_paid = self.db.execute(stmt).one()
        return {
            "total_expected": float(total_expected),
            "total_paid": float(total_paid),
        }
