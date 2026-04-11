from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.permanent_documents.services.permanent_document_action_service import PermanentDocumentActionService
from app.permanent_documents.schemas.permanent_document import (
    DocumentVersionsResponse,
    PermanentDocumentResponse,
    UpdateNotesRequest,
)

router = APIRouter(
    prefix="/documents",
    tags=["permanent-documents"],
)

@router.get(
    "/client/{client_id}/versions",
    response_model=DocumentVersionsResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_document_versions(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
    document_type: str = Query(...),
    tax_year: Optional[int] = Query(default=None),
):
    docs = PermanentDocumentActionService(db).get_document_versions(client_id, document_type, tax_year)
    return DocumentVersionsResponse(items=[PermanentDocumentResponse.model_validate(d) for d in docs])


@router.get(
    "/annual-report/{report_id}",
    response_model=DocumentVersionsResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_by_annual_report(
    report_id: int,
    db: DBSession,
    user: CurrentUser,
):
    docs = PermanentDocumentActionService(db).list_by_annual_report(report_id)
    return DocumentVersionsResponse(items=[PermanentDocumentResponse.model_validate(d) for d in docs])


@router.patch(
    "/{document_id}/notes",
    response_model=PermanentDocumentResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def update_notes(
    document_id: int,
    body: UpdateNotesRequest,
    db: DBSession,
    user: CurrentUser,
):
    doc = PermanentDocumentActionService(db).update_notes(document_id, body.notes)
    return PermanentDocumentResponse.model_validate(doc)
