from fastapi import APIRouter, Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import AnnualReportResponse
from app.annual_reports.services import AnnualReportService


clients_router = APIRouter(
    prefix="/clients",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@clients_router.get("/{client_id}/annual-reports", response_model=list[AnnualReportResponse])
def list_client_reports(client_id: int, db: DBSession, user: CurrentUser):
    """All annual reports for a client, sorted newest year first."""
    service = AnnualReportService(db)
    reports = service.get_client_reports(client_id)
    return [AnnualReportResponse.model_validate(r) for r in reports]
