from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole
from app.reports.services.reports_service import AgingReportService
from app.reports.services.export_service import ExportService
from app.reports.services.annual_report_status_report import AnnualReportStatusReportService
from app.reports.services.advance_payment_report import AdvancePaymentReportService
from app.reports.services.vat_compliance_report import VatComplianceReportService


router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.get("/vat-compliance")
def get_vat_compliance_report(
    db: DBSession,
    year: int = Query(...),
):
    service = VatComplianceReportService(db)
    return service.get_vat_compliance_report(year)


@router.get("/advance-payments")
def get_advance_payment_report(
    db: DBSession,
    year: int = Query(...),
    month: Optional[int] = Query(None),
):
    service = AdvancePaymentReportService(db)
    return service.get_collections_report(year, month)


@router.get("/annual-reports")
def get_annual_report_status_report(
    db: DBSession,
    tax_year: int = Query(...),
):
    service = AnnualReportStatusReportService(db)
    return service.get_report(tax_year)


@router.get("/aging")
def get_aging_report(
    db: DBSession,
    as_of_date: Optional[date] = Query(None),
):
    service = AgingReportService(db)
    return service.generate_aging_report(as_of_date=as_of_date)


@router.get("/aging/export")
def export_aging_report(
    db: DBSession,
    format: str = Query(..., pattern="^(excel|pdf)$"),
    as_of_date: Optional[date] = Query(None),
):
    report_service = AgingReportService(db)
    report = report_service.generate_aging_report(as_of_date=as_of_date)

    export_service = ExportService()

    try:
        if format == "excel":
            result = export_service.export_aging_report_to_excel(report)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            result = export_service.export_aging_report_to_pdf(report)
            media_type = "application/pdf"

        return FileResponse(
            path=result["filepath"],
            media_type=media_type,
            filename=result["filename"],
            headers={
                "Content-Disposition": f'attachment; filename="{result["filename"]}"'
            }
        )

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ספריית הייצוא אינה מותקנת: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"הייצוא נכשל: {str(e)}",
        )
