from fastapi import APIRouter, Depends, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.advance_payments.schemas.advance_payment import (
    GenerateScheduleRequest,
    GenerateScheduleResponse,
)
from app.advance_payments.services.advance_payment_generator import generate_annual_schedule

router = APIRouter(
    prefix="/clients/{client_record_id}/advance-payments",
    tags=["advance-payments"],
)

@router.post(
    "/generate",
    response_model=GenerateScheduleResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def generate_advance_payment_schedule(
    client_record_id: int,
    request: GenerateScheduleRequest,
    db: DBSession,
    user: CurrentUser,
):
    created, skipped = generate_annual_schedule(
        client_record_id,
        request.year,
        db,
        period_months_count=request.period_months_count,
    )
    return GenerateScheduleResponse(created=len(created), skipped=skipped)
