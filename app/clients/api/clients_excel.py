import io

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.schemas.client import ClientImportResponse
from app.clients.services.client_service import ClientService
from app.clients.services.client_excel_service import ClientExcelService

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/export")
def export_clients(db: DBSession, user: CurrentUser):
    """Return all clients as an Excel workbook."""
    client_service = ClientService(db)
    excel_service = ClientExcelService(db)
    try:
        result = excel_service.export_clients(client_service.list_all_clients())
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return FileResponse(
        path=result["filepath"],
        media_type=EXCEL_MEDIA_TYPE,
        filename=result["filename"],
    )


@router.get("/template")
def download_client_template(db: DBSession, user: CurrentUser):
    """Download a starter Excel template for client imports."""
    excel_service = ClientExcelService(db)
    try:
        result = excel_service.generate_template()
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return FileResponse(
        path=result["filepath"],
        media_type=EXCEL_MEDIA_TYPE,
        filename=result["filename"],
    )


MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/import",
    response_model=ClientImportResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
async def import_clients_from_excel(
    file: UploadFile,
    request: Request,
    db: DBSession,
    user: CurrentUser,
):
    """Create clients in bulk from an Excel file (advisor-only)."""
    content_length = request.headers.get("Content-Length")
    if content_length is not None and int(content_length) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="הקובץ חורג ממגבלת הגודל של 10MB",
        )

    try:
        import openpyxl
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="הספרייה openpyxl נדרשת לצורך ייבוא לקוחות",
        ) from exc

    contents = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="הקובץ חורג ממגבלת הגודל של 10MB",
        )
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"לא ניתן לקרוא את קובץ האקסל: {exc}",
        )

    total_rows = max(workbook.active.max_row - 1, 0)
    client_service = ClientService(db)
    excel_service = ClientExcelService(db)
    created, errors = excel_service.import_clients_from_excel(workbook, client_service, actor_id=user.id)

    return {"created": created, "total_rows": total_rows, "errors": errors}
