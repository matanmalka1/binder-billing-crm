from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.schemas.advance_payment import (
    AdvancePaymentOverviewResponse,
    AdvancePaymentOverviewRow,
)
from app.advance_payments.services.advance_payment_analytics_service import AdvancePaymentAnalyticsService

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
            client_id=payment.client_id,
            business_name=business_name,
            period=payment.period,
            period_months_count=payment.period_months_count,
            due_date=payment.due_date,
            expected_amount=payment.expected_amount,
            paid_amount=payment.paid_amount,
            status=payment.status,
        )
        for payment, business_name, _client_id in rows
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