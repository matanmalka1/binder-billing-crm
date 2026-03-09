"""Endpoints for annex (schedule) data lines."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.annual_reports.schemas.annual_report_annex import (
    AnnexDataAddRequest,
    AnnexDataLineResponse,
    AnnexDataUpdateRequest,
)
from app.annual_reports.services.annual_report_service import AnnualReportService


router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get(
    "/{report_id}/annex/{schedule}",
    response_model=list[AnnexDataLineResponse],
)
def list_annex_lines(
    report_id: int,
    schedule: AnnualReportSchedule,
    db: DBSession,
    user: CurrentUser,
):
    svc = AnnualReportService(db)
    try:
        return svc.get_annex_lines(report_id, schedule)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{report_id}/annex/{schedule}",
    response_model=AnnexDataLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_annex_line(
    report_id: int,
    schedule: AnnualReportSchedule,
    body: AnnexDataAddRequest,
    db: DBSession,
    user: CurrentUser,
):
    svc = AnnualReportService(db)
    try:
        return svc.add_annex_line(report_id, schedule, body.data, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{report_id}/annex/{schedule}/{line_id}",
    response_model=AnnexDataLineResponse,
)
def update_annex_line(
    report_id: int,
    schedule: AnnualReportSchedule,
    line_id: int,
    body: AnnexDataUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    svc = AnnualReportService(db)
    try:
        return svc.update_annex_line(report_id, line_id, body.data, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{report_id}/annex/{schedule}/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_annex_line(
    report_id: int,
    schedule: AnnualReportSchedule,
    line_id: int,
    db: DBSession,
    user: CurrentUser,
):
    svc = AnnualReportService(db)
    try:
        svc.delete_annex_line(report_id, line_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
