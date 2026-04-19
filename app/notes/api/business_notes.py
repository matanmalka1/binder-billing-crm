from fastapi import APIRouter, Depends, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_guards import assert_business_belongs_to_legal_entity
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import NotFoundError
from app.notes.schemas.entity_note import (
    EntityNoteCreateRequest,
    EntityNoteListResponse,
    EntityNoteResponse,
    EntityNoteUpdateRequest,
)
from app.notes.services.entity_note_service import EntityNoteService

router = APIRouter(
    prefix="/clients/{client_id}/businesses/{business_id}/notes",
    tags=["notes"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

_ENTITY_TYPE = "business"


def _assert_business_belongs_to_client(db, business_id: int, client_id: int) -> None:
    business = BusinessRepository(db).get_by_id(business_id)
    if not business:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
    record = ClientRecordRepository(db).get_by_client_id(client_id)
    if record is not None:
        assert_business_belongs_to_legal_entity(business, record.legal_entity_id)
    elif business.client_id != client_id:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")


@router.get("", response_model=EntityNoteListResponse)
def list_notes(
    client_id: int,
    business_id: int,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    _assert_business_belongs_to_client(db, business_id, client_id)
    service = EntityNoteService(db)
    items, total = service.list_notes(
        entity_type=_ENTITY_TYPE,
        entity_id=business_id,
        page=page,
        page_size=page_size,
    )
    return EntityNoteListResponse(
        items=[EntityNoteResponse.model_validate(n) for n in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=EntityNoteResponse, status_code=status.HTTP_201_CREATED)
def add_note(
    client_id: int,
    business_id: int,
    request: EntityNoteCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    _assert_business_belongs_to_client(db, business_id, client_id)
    service = EntityNoteService(db)
    note = service.add_note(
        entity_type=_ENTITY_TYPE,
        entity_id=business_id,
        note=request.note,
        created_by=user.id,
    )
    return EntityNoteResponse.model_validate(note)


@router.patch("/{note_id}", response_model=EntityNoteResponse)
def update_note(
    client_id: int,
    business_id: int,
    note_id: int,
    request: EntityNoteUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    _assert_business_belongs_to_client(db, business_id, client_id)
    service = EntityNoteService(db)
    note = service.update_note(
        note_id=note_id,
        entity_type=_ENTITY_TYPE,
        entity_id=business_id,
        note=request.note,
        actor_id=user.id,
    )
    return EntityNoteResponse.model_validate(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    client_id: int,
    business_id: int,
    note_id: int,
    db: DBSession,
    user: CurrentUser,
):
    _assert_business_belongs_to_client(db, business_id, client_id)
    service = EntityNoteService(db)
    service.delete_note(
        note_id=note_id,
        entity_type=_ENTITY_TYPE,
        entity_id=business_id,
        actor_id=user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
