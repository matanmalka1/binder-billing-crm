from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.schemas.dashboard_tax import TaxSubmissionWidgetResponse
from app.services.dashboard_tax_service import DashboardTaxService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard-tax"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/tax-submissions", response_model=TaxSubmissionWidgetResponse)
def get_tax_submission_widget(
    db: DBSession,
    user: CurrentUser,
    tax_year: Optional[int] = Query(None, ge=1900),
):
    """Return tax submission statistics for the dashboard."""
    service = DashboardTaxService(db)
    response = service.get_submission_widget_data(tax_year=tax_year)
    return TaxSubmissionWidgetResponse(**response)
