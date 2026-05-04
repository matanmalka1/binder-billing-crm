from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.schemas.advance_payment import (
    AdvancePaymentOverviewResponse,
    AdvancePaymentOverviewRow,
    MonthBatchSummary,
)
from app.advance_payments.services.advance_payment_analytics_service import AdvancePaymentAnalyticsService
from app.advance_payments.repositories.advance_payment_aggregation_repository import AdvancePaymentAggregationRepository

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
    status: list[str] | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    resolved_statuses = [AdvancePaymentStatus(s) for s in status] if status else None

    service = AdvancePaymentAnalyticsService(db)
    rows, total = service.list_overview(
        year=year,
        month=month,
        statuses=resolved_statuses,
        page=page,
        page_size=page_size,
    )
    kpis = service.get_overview_kpis(year=year, month=month, statuses=resolved_statuses)

    items = [
        AdvancePaymentOverviewRow(
            id=payment.id,
            client_record_id=payment.client_record_id,
            office_client_number=office_client_number,
            business_name=business_name,
            id_number=id_number,
            period=payment.period,
            period_months_count=payment.period_months_count,
            due_date=payment.due_date,
            expected_amount=payment.expected_amount,
            paid_amount=payment.paid_amount,
            status=payment.status,
            payment_method=payment.payment_method,
            reported_turnover=payment.reported_turnover,
            live_turnover=live_turnover,
            missing_turnover=(
                payment.reported_turnover is None and live_turnover is None
            ),
            advance_rate=advance_rate,
        )
        for payment, office_client_number, business_name, id_number, live_turnover, advance_rate in rows
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
    year: int = Query(...),
):
    rows = AdvancePaymentAggregationRepository(db).batch_summary_by_month(year)
    result = []
    for r in rows:
        total_expected = float(r.total_expected)
        total_paid = float(r.total_paid)
        collection_rate = round(total_paid / total_expected * 100, 2) if total_expected > 0 else 0.0
        result.append(MonthBatchSummary(
            year=year,
            month=int(r.month),
            client_count=int(r.client_count),
            missing_turnover_count=int(r.snapshot_missing_count or 0),
            overdue_count=int(r.overdue_count or 0),
            pending_count=int(r.pending_count or 0),
            total_expected=total_expected,
            total_paid=total_paid,
            collection_rate=collection_rate,
        ))
    return result
