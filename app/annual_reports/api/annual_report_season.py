from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas.annual_report_responses import AnnualReportListResponse, SeasonSummaryResponse
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.annual_reports.services.season_years import get_active_annual_report_tax_year


season_router = APIRouter(
    prefix="/tax-year",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@season_router.get("/active/reports", response_model=AnnualReportListResponse)
def list_active_season_reports(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    tax_year = get_active_annual_report_tax_year()
    service = AnnualReportService(db)
    items, total = service.list_reports(tax_year=tax_year, page=page, page_size=page_size)
    return AnnualReportListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@season_router.get("/active/summary", response_model=SeasonSummaryResponse)
def get_active_season_summary(db: DBSession, user: CurrentUser):
    tax_year = get_active_annual_report_tax_year()
    return AnnualReportService(db).get_season_summary_response(tax_year)


@season_router.get("/{tax_year}/reports", response_model=AnnualReportListResponse)
def list_season_reports(
    tax_year: int,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    """All reports for a given tax year — the advisor's season dashboard."""
    service = AnnualReportService(db)
    items, total = service.list_reports(tax_year=tax_year, page=page, page_size=page_size)
    return AnnualReportListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@season_router.get("/{tax_year}/summary", response_model=SeasonSummaryResponse)
def get_season_summary(tax_year: int, db: DBSession, user: CurrentUser):
    return AnnualReportService(db).get_season_summary_response(tax_year)
