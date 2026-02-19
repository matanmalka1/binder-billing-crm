from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.schemas.advance_payment import (
    AdvancePaymentListResponse,
    AdvancePaymentRow,
    AdvancePaymentUpdateRequest,
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


@router.patch("/{payment_id}", response_model=AdvancePaymentRow)
def update_advance_payment(
    payment_id: int,
    request: AdvancePaymentUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    if request.status is not None:
        try:
            AdvancePaymentStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {request.status}",
            )
    service = AdvancePaymentService(db)
    try:
        update_data = request.model_dump(exclude_unset=True)
        payment = service.update_payment(payment_id, **update_data)
        return AdvancePaymentRow.model_validate(payment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
