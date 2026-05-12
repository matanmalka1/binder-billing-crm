from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.tax_calendar.schemas.settings import (
    TaxCalendarBootstrapRequest,
    TaxCalendarBootstrapResponse,
    DeadlineRuleResponse,
    TaxCalendarEntryResponse,
    TaxCalendarSummaryResponse,
)
from app.tax_calendar.services import settings_calendar_service
from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole

router = APIRouter(prefix="/settings/tax-calendar", tags=["settings-tax-calendar"])


def _check_year_range(start_year: int | None, end_year: int | None) -> None:
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="שנת ההתחלה חייבת להיות קטנה או שווה לשנת הסיום.",
        )


@router.get(
    "/rules",
    response_model=list[DeadlineRuleResponse],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def list_deadline_rules(db: DBSession) -> list[DeadlineRuleResponse]:
    return settings_calendar_service.list_rules(db)


@router.get(
    "/entries",
    response_model=list[TaxCalendarEntryResponse],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def list_tax_calendar_entries(
    db: DBSession,
    start_year: int | None = Query(None),
    end_year: int | None = Query(None),
) -> list[TaxCalendarEntryResponse]:
    _check_year_range(start_year, end_year)
    return settings_calendar_service.list_entries(
        db, start_year=start_year, end_year=end_year
    )


@router.get(
    "/summary",
    response_model=TaxCalendarSummaryResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def get_tax_calendar_summary(
    db: DBSession,
    start_year: int | None = Query(None),
    end_year: int | None = Query(None),
) -> TaxCalendarSummaryResponse:
    _check_year_range(start_year, end_year)
    return settings_calendar_service.get_summary(
        db, start_year=start_year, end_year=end_year
    )


@router.post(
    "/bootstrap",
    response_model=TaxCalendarBootstrapResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def bootstrap_tax_calendar_settings(
    request: TaxCalendarBootstrapRequest,
    db: DBSession,
    _x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
) -> TaxCalendarBootstrapResponse:
    _check_year_range(request.start_year, request.end_year)
    return settings_calendar_service.bootstrap_calendar(
        db, start_year=request.start_year, end_year=request.end_year
    )
