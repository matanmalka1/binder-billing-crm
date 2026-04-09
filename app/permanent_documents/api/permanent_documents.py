from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.permanent_documents.schemas.permanent_document import (
    DocumentDownloadUrlResponse,
    OperationalSignalsResponse,
    PermanentDocumentListResponse,
    PermanentDocumentResponse,
)
from app.permanent_documents.services.permanent_document_service import PermanentDocumentService

router = APIRouter(
    prefix="/documents",
    tags=["permanent-documents"],
)


@router.post(
    "/upload",
    response_model=PermanentDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def upload_permanent_document(
    business_id: Annotated[int, Form(...)],
    document_type: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db: DBSession,
    user: CurrentUser,
    tax_year: Annotated[Optional[int], Form()] = None,
    annual_report_id: Annotated[Optional[int], Form()] = None,
    notes: Annotated[Optional[str], Form()] = None,
):
    """Upload permanent document (ADVISOR and SECRETARY)."""
    service = PermanentDocumentService(db)
    document = service.upload_document(
        business_id=business_id,
        document_type=document_type,
        file_data=file.file,
        filename=file.filename or "document",
        uploaded_by=user.id,
        tax_year=tax_year,
        annual_report_id=annual_report_id,
        notes=notes,
        mime_type=file.content_type,
    )
    return PermanentDocumentResponse.model_validate(document)


@router.get(
    "/client/{client_id}",
    response_model=PermanentDocumentListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_client_documents(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
    tax_year: Optional[int] = Query(default=None),
):
    """List permanent documents for a client."""
    service = PermanentDocumentService(db)
    documents = service.list_client_documents(client_id, tax_year=tax_year)

    return PermanentDocumentListResponse(
        items=[PermanentDocumentResponse.model_validate(doc) for doc in documents]
    )


@router.get(
    "/client/{client_id}/signals",
    response_model=OperationalSignalsResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_operational_signals(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """Get operational signals for a client (advisory indicators)."""
    signals = PermanentDocumentService(db).get_client_operational_signals(client_id)
    return OperationalSignalsResponse(**signals)


@router.get(
    "/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_download_url(document_id: int, db: DBSession, user: CurrentUser):
    """Get a presigned download URL for a document (expires in 1 hour)."""
    url = PermanentDocumentService(db).get_download_url(document_id)
    return {"url": url}


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_document(document_id: int, db: DBSession, user: CurrentUser):
    """Soft-delete a permanent document (ADVISOR only)."""
    PermanentDocumentService(db).delete_document(document_id)


@router.put(
    "/{document_id}/replace",
    response_model=PermanentDocumentResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def replace_document(
    document_id: int,
    file: Annotated[UploadFile, File(...)],
    db: DBSession,
    user: CurrentUser,
):
    """Replace the file for an existing document (ADVISOR only)."""
    doc = PermanentDocumentService(db).replace_document(
        document_id=document_id,
        file_data=file.file,
        filename=file.filename or "document",
        uploaded_by=user.id,
        mime_type=file.content_type,
    )
    return PermanentDocumentResponse.model_validate(doc)
