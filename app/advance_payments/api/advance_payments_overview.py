from datetime import date

from fastapi import APIRouter, Depends, Query

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_batch_repository import (
    AdvancePaymentBatchRepository,
)
from app.advance_payments.schemas.advance_payment import (
    AdvancePaymentOverviewResponse,
    AdvancePaymentOverviewRow,
    MonthBatchSummary,
)
from app.advance_payments.services.advance_payment_analytics_service import (
    AdvancePaymentAnalyticsService,
)
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole

overview_router = APIRouter(
    prefix="/advance-payments",
    tags=["advance-payments"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@overview_router.get("/overview", response_model=AdvancePaymentOverviewResponse)
def list_advance_payments_overview(
    db: DBSession,
    user: CurrentUser,
    year: int = Query(...),
    month: int | None = Query(None, ge=1, le=12),
    due_date: date | None = Query(None),
    period_months_count: int | None = Query(None, ge=1, le=2),
    client_search: str | None = Query(None),
    status: list[AdvancePaymentStatus] | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    resolved_statuses = status if status else None

    service = AdvancePaymentAnalyticsService(db)
    rows, total = service.list_overview(
        year=year,
        month=month,
        due_date=due_date,
        period_months_count=period_months_count,
        client_search=client_search,
        statuses=resolved_statuses,
        page=page,
        page_size=page_size,
    )
    kpis = service.get_overview_kpis(
        year=year,
        month=month,
        statuses=resolved_statuses,
        due_date=due_date,
        period_months_count=period_months_count,
        client_search=client_search,
    )

    items = [
        AdvancePaymentOverviewRow(
            id=row.payment.id,
            client_record_id=row.payment.client_record_id,
            office_client_number=row.office_client_number,
            business_name=row.business_name,
            id_number=row.id_number,
            period=row.payment.period,
            period_months_count=row.payment.period_months_count,
            due_date=row.payment.due_date,
            expected_amount=row.payment.expected_amount,
            paid_amount=row.payment.paid_amount,
            status=row.payment.status,
            payment_method=row.payment.payment_method,
            turnover_amount=row.payment.turnover_amount,
            calculated_amount=row.payment.calculated_amount,
            override_amount=row.payment.override_amount,
            live_turnover=row.live_turnover,
            missing_turnover=(row.payment.turnover_amount is None and row.live_turnover is None),
            advance_rate=row.advance_rate,
        )
        for row in rows
    ]
    return AdvancePaymentOverviewResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_expected=kpis["total_expected"],
        total_paid=kpis["total_paid"],
        collection_rate=kpis["collection_rate"],
    )


@overview_router.get("/overview/batches", response_model=list[MonthBatchSummary])
def list_advance_payment_batches(
    db: DBSession,
    user: CurrentUser,
    year: int | None = Query(None),
):
    rows = AdvancePaymentBatchRepository(db).batch_summary_by_month(year)
    result = []
    for r in rows:
        total_expected = float(r.total_expected)
        total_paid = float(r.total_paid)
        collection_rate = round(total_paid / total_expected * 100, 2) if total_expected > 0 else 0.0
        result.append(
            MonthBatchSummary(
                year=int(r.year),
                month=int(r.month),
                due_date=r.due_date,
                period_months_count=int(r.period_months_count or 1),
                client_count=int(r.client_count),
                missing_turnover_count=int(r.snapshot_missing_count or 0),
                overdue_count=int(r.overdue_count or 0),
                pending_count=int(r.pending_count or 0),
                paid_count=int(r.paid_count or 0),
                not_paid_count=int(r.client_count) - int(r.paid_count or 0),
                total_expected=total_expected,
                total_paid=total_paid,
                collection_rate=collection_rate,
            )
        )
    return result
