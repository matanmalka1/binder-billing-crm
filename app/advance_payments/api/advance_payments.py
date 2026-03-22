from fastapi import APIRouter, Depends, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.schemas.advance_payment import (
    AdvancePaymentCreateRequest,
    AdvancePaymentListResponse,
    AdvancePaymentRow,
    AdvancePaymentSuggestionResponse,
    AdvancePaymentUpdateRequest,
    AnnualKPIResponse,
    ChartDataResponse,
)
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.core.exceptions import AppError

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
    if request.business_id != business_id:
        raise AppError("business_id בגוף הבקשה חייב להיות זהה ל-business_id בנתיב", "ADVANCE_PAYMENT.BUSINESS_ID_MISMATCH")

    service = AdvancePaymentService(db)
    payment = service.create_payment(
        business_id=business_id,
        period=request.period,
        period_months_count=request.period_months_count,
        due_date=request.due_date,
        expected_amount=request.expected_amount,
        paid_amount=request.paid_amount,
        payment_method=request.payment_method,
        annual_report_id=request.annual_report_id,
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
    payment = service.update_payment(
        business_id=business_id,
        payment_id=payment_id,
        **request.model_dump(exclude_unset=True),
    )
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
    AdvancePaymentService(db).delete_payment(business_id, payment_id, actor_id=user.id)