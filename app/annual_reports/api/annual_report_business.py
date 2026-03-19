from fastapi import APIRouter, Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import AnnualReportResponse
from app.annual_reports.services import AnnualReportService


businesses_router = APIRouter(
    prefix="/businesses",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@businesses_router.get("/{business_id}/annual-reports", response_model=list[AnnualReportResponse])
def list_business_reports(business_id: int, db: DBSession, user: CurrentUser):
    """All annual reports for a business, sorted newest year first."""
    service = AnnualReportService(db)
    return service.get_business_reports(business_id)