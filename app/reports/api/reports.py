from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.reports.services.reports_service import AgingReportService
from app.reports.services.export_service import ExportService


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
    format: str = Query(..., pattern="^(excel|pdf)$"),
    as_of_date: Optional[date] = Query(None),
):
    """
    Export aging report to Excel or PDF.
    
    ADVISOR only.
    Returns file directly for download.
    """
    
 # Generate report data
    report_service = AgingReportService(db)
    report = report_service.generate_aging_report(as_of_date=as_of_date)

    # Export to requested format
    export_service = ExportService(db)
    
    try:
        if format == "excel":
            result = export_service.export_aging_report_to_excel(report)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format == "pdf":
            result = export_service.export_aging_report_to_pdf(report)
            media_type = "application/pdf"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format. Use 'excel' or 'pdf'",
            )
        
        # Return file directly as download
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
            detail=f"Export library not installed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )
