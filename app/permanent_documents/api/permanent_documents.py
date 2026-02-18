from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from io import BytesIO

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.models import DocumentType, UserRole
from app.schemas import (
    OperationalSignalsResponse,
    PermanentDocumentListResponse,
    PermanentDocumentResponse,
)
from app.permanent_documents.services.permanent_document_service import (
    PermanentDocumentService,
)
from app.binders.services.signals_service import SignalsService

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
    client_id: Annotated[int, Form(...)],
    document_type: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db: DBSession,
    user: CurrentUser,
):
    """Upload permanent document (ADVISOR and SECRETARY)."""
    service = PermanentDocumentService(db)

    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type: {document_type}",
        )

    try:
        file_data = BytesIO(file.file.read())
        document = service.upload_document(
            client_id=client_id,
            document_type=doc_type,
            file_data=file_data,
            filename=file.filename or "document",
            uploaded_by=user.id,
        )
        return PermanentDocumentResponse.model_validate(document)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/client/{client_id}",
    response_model=PermanentDocumentListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_client_documents(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """List permanent documents for a client."""
    service = PermanentDocumentService(db)
    documents = service.list_client_documents(client_id)

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
    service = SignalsService(db)
    signals = service.compute_client_operational_signals(client_id)

    return OperationalSignalsResponse(**signals)
