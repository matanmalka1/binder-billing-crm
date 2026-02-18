from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import (  # FIXED: was app.schemas.annual_report
    AnnualReportListResponse,
    AnnualReportResponse,
    SeasonSummaryResponse,
)
from app.annual_reports.services import AnnualReportService


season_router = APIRouter(
    prefix="/tax-year",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@season_router.get("/{tax_year}/reports", response_model=AnnualReportListResponse)
def list_season_reports(
    tax_year: int,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """All reports for a given tax year — the advisor's season dashboard."""
    service = AnnualReportService(db)
    items, total = service.get_season_reports(tax_year, page=page, page_size=page_size)
    return AnnualReportListResponse(
        items=[AnnualReportResponse.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@season_router.get("/{tax_year}/summary", response_model=SeasonSummaryResponse)
def get_season_summary(tax_year: int, db: DBSession, user: CurrentUser):
    """
    Aggregated progress for a tax year.

    Shows how many reports are in each status, the completion rate,
    and how many are overdue — essential for the season progress dashboard.
    """
    service = AnnualReportService(db)
    summary = service.get_season_summary(tax_year)
    overdue = len(service.get_overdue(tax_year=tax_year))

    total = summary.get("total", 0)
    done = (
        summary.get("submitted", 0)
        + summary.get("accepted", 0)
        + summary.get("closed", 0)
    )
    rate = round(done / total * 100, 1) if total > 0 else 0.0

    return SeasonSummaryResponse(
        tax_year=tax_year,
        total=total,
        not_started=summary.get("not_started", 0),
        collecting_docs=summary.get("collecting_docs", 0),
        docs_complete=summary.get("docs_complete", 0),
        in_preparation=summary.get("in_preparation", 0),
        pending_client=summary.get("pending_client", 0),
        submitted=summary.get("submitted", 0),
        accepted=summary.get("accepted", 0),
        assessment_issued=summary.get("assessment_issued", 0),
        objection_filed=summary.get("objection_filed", 0),
        closed=summary.get("closed", 0),
        completion_rate=rate,
        overdue_count=overdue,
    )