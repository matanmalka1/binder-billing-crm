from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.constants import EXCEL_MEDIA_TYPE, MAX_CLIENT_IMPORT_UPLOAD_SIZE
from app.clients.schemas.client import ClientImportResponse
from app.clients.services.client_excel_service import ClientExcelImportError, ClientExcelService
from app.clients.services.create_client_service import CreateClientService
from app.clients.services.client_service import ClientService

MAX_UPLOAD_SIZE = MAX_CLIENT_IMPORT_UPLOAD_SIZE

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

@router.get("/export")
def export_clients(db: DBSession):
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
def download_client_template(db: DBSession):
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
    _x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
):
    """Create clients in bulk from an Excel file (advisor-only)."""
    content_length = request.headers.get("Content-Length")
    parsed_content_length = int(content_length) if content_length is not None else None
    contents = await file.read(MAX_UPLOAD_SIZE + 1)
    create_client_service = CreateClientService(db)
    excel_service = ClientExcelService(db)

    try:
        return excel_service.import_clients_from_upload(
            contents,
            create_client_service,
            actor_id=user.id,
            content_length=parsed_content_length,
            max_upload_size=MAX_UPLOAD_SIZE,
        )
    except ClientExcelImportError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc
