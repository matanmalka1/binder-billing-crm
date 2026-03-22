from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import AnnualReportListResponse
from app.annual_reports.services import AnnualReportService


businesses_router = APIRouter(
    prefix="/businesses",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@businesses_router.get("/{business_id}/annual-reports", response_model=AnnualReportListResponse)
def list_business_reports(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """All annual reports for a business, sorted newest year first."""
    service = AnnualReportService(db)
    items, total = service.get_business_reports(business_id, page=page, page_size=page_size)
    return AnnualReportListResponse(items=items, page=page, page_size=page_size, total=total)