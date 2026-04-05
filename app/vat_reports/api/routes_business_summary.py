"""Routes: business-level VAT summary and export."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.core.logging_config import get_logger
from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole
from app.vat_reports.schemas.vat_client_summary_schema import VatBusinessSummaryResponse
from app.vat_reports.services.vat_client_summary_service import get_business_summary
from app.vat_reports.services.vat_export_service import export

logger = get_logger(__name__)

router = APIRouter(
    prefix="/vat",
    tags=["vat-reports"],
)


@router.get(
    "/businesses/{business_id}/summary",
    response_model=VatBusinessSummaryResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_vat_business_summary(
    business_id: int,
    db: DBSession,
):
    return get_business_summary(db, business_id=business_id)


@router.get(
    "/businesses/{business_id}/export",
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def export_vat_business(
    business_id: int,
    db: DBSession,
    format: str = Query(..., pattern="^(excel|pdf)$"),
    year: int = Query(..., ge=2000, le=2100),
):
    result, media_type = export(db, business_id, year, fmt=format)
    return FileResponse(
        path=result["filepath"],
        media_type=media_type,
        filename=result["filename"],
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )
