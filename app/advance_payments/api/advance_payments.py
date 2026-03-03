from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.advance_payments.schemas.advance_payment import (
    AdvancePaymentListResponse,
    AdvancePaymentRow,
    AdvancePaymentUpdateRequest,
    AdvancePaymentCreateRequest,
)
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.utils.time import utcnow

router = APIRouter(
    prefix="/advance-payments",
    tags=["advance-payments"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=AdvancePaymentListResponse)
def list_advance_payments(
    db: DBSession,
    user: CurrentUser,
    client_id: int = Query(...),
    year: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    from app.clients.repositories.client_repository import ClientRepository

    client = ClientRepository(db).get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if year is None:
        year = utcnow().year

    service = AdvancePaymentService(db)
    items = service.list_payments(client_id, year)
    total = len(items)
    offset = (page - 1) * page_size
    paginated = items[offset: offset + page_size]

    return AdvancePaymentListResponse(
        items=[AdvancePaymentRow.model_validate(p) for p in paginated],
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
    request: AdvancePaymentCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = AdvancePaymentService(db)
    try:
        payment = service.create_payment(
            client_id=request.client_id,
            year=request.year,
            month=request.month,
            due_date=request.due_date,
            expected_amount=request.expected_amount,
            paid_amount=request.paid_amount,
            tax_deadline_id=request.tax_deadline_id,
        )
        return AdvancePaymentRow.model_validate(payment)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{payment_id}", response_model=AdvancePaymentRow)
def update_advance_payment(
    payment_id: int,
    request: AdvancePaymentUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = AdvancePaymentService(db)
    try:
        update_data = request.model_dump(exclude_unset=True)
        payment = service.update_payment(payment_id, **update_data)
        return AdvancePaymentRow.model_validate(payment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
