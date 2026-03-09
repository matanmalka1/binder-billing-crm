"""Routes: client-level VAT summary and export."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.clients.repositories.client_repository import ClientRepository
from app.core.logging import get_logger
from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole
from app.vat_reports.repositories.vat_client_summary_repository import (
    VatClientSummaryRepository,
)
from app.vat_reports.schemas.vat_client_summary_schema import VatClientSummaryResponse
from app.vat_reports.services.vat_client_summary_service import get_client_summary
from app.vat_reports.services.vat_export_service import export_to_excel, export_to_pdf

logger = get_logger(__name__)

router = APIRouter(
    prefix="/vat",
    tags=["vat-reports"],
)


@router.get(
    "/client/{client_id}/summary",
    response_model=VatClientSummaryResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_vat_client_summary(
    client_id: int,
    db: DBSession,
):
    summary_repo = VatClientSummaryRepository(db)
    client_repo = ClientRepository(db)
    return get_client_summary(summary_repo, client_repo, client_id=client_id)


@router.get(
    "/client/{client_id}/export",
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def export_vat_client(
    client_id: int,
    db: DBSession,
    format: str = Query(..., pattern="^(excel|pdf)$"),
    year: int = Query(..., ge=2000, le=2100),
):
    try:
        if format == "excel":
            result = export_to_excel(db, client_id, year)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            result = export_to_pdf(db, client_id, year)
            media_type = "application/pdf"
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except Exception:
        logger.exception("VAT export failed for client_id=%s year=%s", client_id, year)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="הייצוא נכשל. יש לנסות שוב.",
        )

    return FileResponse(
        path=result["filepath"],
        media_type=media_type,
        filename=result["filename"],
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )
