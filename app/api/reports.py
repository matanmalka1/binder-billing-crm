from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.services.reports_service import AgingReportService
from app.services.export_service import ExportService


router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.get("/aging")
def get_aging_report(
    db: DBSession,
    user: CurrentUser,
    as_of_date: Optional[date] = Query(None),
):
    """
    Generate aging report for outstanding charges.
    
    ADVISOR only. Shows debt aging by buckets:
    - Current (0-30 days)
    - 30 days (31-60)
    - 60 days (61-90)
    - 90+ days
    """
    
    service = AgingReportService(db)
    report = service.generate_aging_report(as_of_date=as_of_date)
    
    return report


@router.get("/aging/export")
def export_aging_report(
    db: DBSession,
    user: CurrentUser,
    format: str = Query(..., regex="^(excel|pdf)$"),
    as_of_date: Optional[date] = Query(None),
):
    """
    Export aging report to Excel or PDF.
    
    ADVISOR only.
    """

    
    # Generate report data
    report_service = AgingReportService(db)
    report = report_service.generate_aging_report(as_of_date=as_of_date)
    
    # Export to requested format
    export_service = ExportService(db)
    
    try:
        if format == "excel":
            result = export_service.export_aging_report_to_excel(report)
        elif format == "pdf":
            result = export_service.export_aging_report_to_pdf(report)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format. Use 'excel' or 'pdf'",
            )
        
        return result
        
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export library not installed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )
