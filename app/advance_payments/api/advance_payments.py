from fastapi import APIRouter, Depends, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.schemas.advance_payment import (
    AdvancePaymentCreateRequest,
    AdvancePaymentListResponse,
    AdvancePaymentOverviewResponse,
    AdvancePaymentOverviewRow,
    AdvancePaymentRow,
    AdvancePaymentSuggestionResponse,
    AdvancePaymentUpdateRequest,
    AnnualKPIResponse,
    ChartDataResponse,
    GenerateScheduleRequest,
    GenerateScheduleResponse,
)
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.advance_payments.services.advance_payment_generator import generate_annual_schedule
from app.utils.time_utils import utcnow

# ─── Nested under /businesses/{business_id}/advance-payments ─────────────────

router = APIRouter(
    prefix="/businesses/{business_id}/advance-payments",
    tags=["advance-payments"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=AdvancePaymentListResponse)
def list_advance_payments(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    year: int | None = Query(None),
    status_filter: list[AdvancePaymentStatus] = Query(default=[], alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    if year is None:
        year = utcnow().year

    service = AdvancePaymentService(db)
    items, total = service.list_payments(
        business_id,
        year,
        status=status_filter if status_filter else None,
        page=page,
        page_size=page_size,
    )
    return AdvancePaymentListResponse(
        items=[AdvancePaymentRow.model_validate(p) for p in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "",
    response_model=AdvancePaymentRow,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def create_advance_payment(
    business_id: int,
    request: AdvancePaymentCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = AdvancePaymentService(db)
    payment = service.create_payment(
        business_id=business_id,
        year=request.year,
        month=request.month,
        due_date=request.due_date,
        expected_amount=request.expected_amount,
        paid_amount=request.paid_amount,
        tax_deadline_id=request.tax_deadline_id,
        notes=request.notes,
    )
    return AdvancePaymentRow.model_validate(payment)


@router.get("/suggest", response_model=AdvancePaymentSuggestionResponse)
def suggest_advance_payment(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    year: int = Query(...),
):
    service = AdvancePaymentService(db)
    suggested = service.suggest_expected_amount(business_id, year)
    return AdvancePaymentSuggestionResponse(
        business_id=business_id,
        year=year,
        suggested_amount=suggested,
        has_data=suggested is not None,
    )


@router.post(
    "/generate",
    response_model=GenerateScheduleResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def generate_advance_payment_schedule(
    business_id: int,
    request: GenerateScheduleRequest,
    db: DBSession,
    user: CurrentUser,
):
    created, skipped = generate_annual_schedule(business_id, request.year, db)
    return GenerateScheduleResponse(created=len(created), skipped=skipped)


@router.get("/kpi", response_model=AnnualKPIResponse)
def get_annual_kpis(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    year: int = Query(...),
):
    service = AdvancePaymentService(db)
    data = service.get_annual_kpis(business_id=business_id, year=year)
    return AnnualKPIResponse(**data)


@router.get("/chart", response_model=ChartDataResponse)
def get_chart_data(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    year: int = Query(...),
):
    service = AdvancePaymentService(db)
    data = service.get_chart_data(business_id=business_id, year=year)
    return ChartDataResponse(**data)


@router.patch(
    "/{payment_id}",
    response_model=AdvancePaymentRow,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def update_advance_payment(
    business_id: int,
    payment_id: int,
    request: AdvancePaymentUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = AdvancePaymentService(db)
    payment = service.update_payment(payment_id, **request.model_dump(exclude_unset=True))
    return AdvancePaymentRow.model_validate(payment)


@router.delete(
    "/{payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_advance_payment(
    business_id: int,
    payment_id: int,
    db: DBSession,
    user: CurrentUser,
):
    AdvancePaymentService(db).delete_payment(payment_id, actor_id=user.id)


# ─── Standalone /advance-payments (overview — cross-business) ─────────────────

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
    page_size: int = Query(50, ge=1, le=200),
):
    resolved_statuses = [AdvancePaymentStatus(s) for s in status] if status else None

    service = AdvancePaymentService(db)
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
            business_id=payment.business_id,
            business_name=business_name,
            month=payment.month,
            year=payment.year,
            expected_amount=float(payment.expected_amount) if payment.expected_amount is not None else None,
            paid_amount=float(payment.paid_amount) if payment.paid_amount is not None else None,
            status=payment.status,
            due_date=payment.due_date,
        )
        for payment, business_name in rows
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