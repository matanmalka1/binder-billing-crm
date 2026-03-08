from fastapi import HTTPException, Query

from app.users.api.deps import CurrentUser, DBSession
from app.advance_payments.schemas.advance_payment import (
    AdvancePaymentOverviewResponse,
    AdvancePaymentOverviewRow,
)
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.api.advance_payments import router


@router.get("/overview", response_model=AdvancePaymentOverviewResponse)
def list_advance_payments_overview(
    db: DBSession,
    user: CurrentUser,
    year: int = Query(...),
    month: int | None = Query(None, ge=1, le=12),
    status: list[str] | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    resolved_statuses = None
    if status:
        try:
            resolved_statuses = [AdvancePaymentStatus(s) for s in status]
        except ValueError:
            raise HTTPException(status_code=400, detail="סטטוס לא חוקי")

    service = AdvancePaymentService(db)
    rows, total = service.list_overview(
        year=year,
        month=month,
        statuses=resolved_statuses,
        page=page,
        page_size=page_size,
    )
    items = [
        AdvancePaymentOverviewRow(
            id=payment.id,
            client_id=payment.client_id,
            client_name=client_name,
            month=payment.month,
            year=payment.year,
            expected_amount=float(payment.expected_amount) if payment.expected_amount is not None else None,
            paid_amount=float(payment.paid_amount) if payment.paid_amount is not None else None,
            status=payment.status,
            due_date=payment.due_date,
        )
        for payment, client_name in rows
    ]
    return AdvancePaymentOverviewResponse(
        items=items, page=page, page_size=page_size, total=total
    )
