"""Endpoints for income lines, expense lines, financial summary, and readiness check."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas.annual_report_financials import (
    ExpenseLineCreateRequest,
    ExpenseLineResponse,
    ExpenseLineUpdateRequest,
    FinancialSummaryResponse,
    IncomeLineCreateRequest,
    IncomeLineResponse,
    IncomeLineUpdateRequest,
    ReadinessCheckResponse,
)
from app.annual_reports.services.financial_service import AnnualReportFinancialService


router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


# ── Financial summary ─────────────────────────────────────────────────────────

@router.get("/{report_id}/financials", response_model=FinancialSummaryResponse)
def get_financial_summary(report_id: int, db: DBSession, user: CurrentUser):
    """Income + expense lines and taxable income calculation."""
    svc = AnnualReportFinancialService(db)
    try:
        return svc.get_financial_summary(report_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Readiness check ───────────────────────────────────────────────────────────

@router.get("/{report_id}/readiness", response_model=ReadinessCheckResponse)
def get_readiness_check(report_id: int, db: DBSession, user: CurrentUser):
    """Return list of issues blocking this report from being filed."""
    svc = AnnualReportFinancialService(db)
    try:
        return svc.get_readiness_check(report_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Income lines ──────────────────────────────────────────────────────────────

@router.post(
    "/{report_id}/income",
    response_model=IncomeLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_income_line(report_id: int, body: IncomeLineCreateRequest, db: DBSession, user: CurrentUser):
    svc = AnnualReportFinancialService(db)
    try:
        return svc.add_income(report_id, body.source_type, body.amount, body.description)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{report_id}/income/{line_id}", response_model=IncomeLineResponse)
def update_income_line(
    report_id: int, line_id: int, body: IncomeLineUpdateRequest, db: DBSession, user: CurrentUser
):
    svc = AnnualReportFinancialService(db)
    try:
        return svc.update_income(report_id, line_id, **body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{report_id}/income/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_income_line(report_id: int, line_id: int, db: DBSession, user: CurrentUser):
    svc = AnnualReportFinancialService(db)
    try:
        svc.delete_income(report_id, line_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Expense lines ─────────────────────────────────────────────────────────────

@router.post(
    "/{report_id}/expenses",
    response_model=ExpenseLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_expense_line(report_id: int, body: ExpenseLineCreateRequest, db: DBSession, user: CurrentUser):
    svc = AnnualReportFinancialService(db)
    try:
        return svc.add_expense(report_id, body.category, body.amount, body.description)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{report_id}/expenses/{line_id}", response_model=ExpenseLineResponse)
def update_expense_line(
    report_id: int, line_id: int, body: ExpenseLineUpdateRequest, db: DBSession, user: CurrentUser
):
    svc = AnnualReportFinancialService(db)
    try:
        return svc.update_expense(report_id, line_id, **body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{report_id}/expenses/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_expense_line(report_id: int, line_id: int, db: DBSession, user: CurrentUser):
    svc = AnnualReportFinancialService(db)
    try:
        svc.delete_expense(report_id, line_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
