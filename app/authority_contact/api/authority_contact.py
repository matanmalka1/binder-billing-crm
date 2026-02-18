from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.models import ContactType, UserRole
from app.authority_contact.schemas.authority_contact import (
    AuthorityContactCreateRequest,
    AuthorityContactListResponse,
    AuthorityContactResponse,
    AuthorityContactUpdateRequest,
)
from app.authority_contact.services.authority_contact_service import AuthorityContactService

router = APIRouter(
    prefix="/clients",
    tags=["authority-contacts"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.post(
    "/{client_id}/authority-contacts",
    response_model=AuthorityContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_authority_contact(
    client_id: int,
    request: AuthorityContactCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Create new authority contact for client."""
    service = AuthorityContactService(db)

    try:
        contact_type = ContactType(request.contact_type)
        contact = service.add_contact(
            client_id=client_id,
            contact_type=contact_type,
            name=request.name,
            office=request.office,
            phone=request.phone,
            email=request.email,
            notes=request.notes,
        )
        return AuthorityContactResponse.model_validate(contact)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{client_id}/authority-contacts", response_model=AuthorityContactListResponse)
def list_authority_contacts(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
    contact_type: Optional[str] = None,
):
    """List authority contacts for client."""
    service = AuthorityContactService(db)

    type_enum = None
    if contact_type:
        try:
            type_enum = ContactType(contact_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid contact type: {contact_type}",
            )

    contacts = service.list_client_contacts(client_id, type_enum)

    return AuthorityContactListResponse(
        items=[AuthorityContactResponse.model_validate(c) for c in contacts]
    )


@router.patch(
    "/authority-contacts/{contact_id}",
    response_model=AuthorityContactResponse,
)
def update_authority_contact(
    contact_id: int,
    request: AuthorityContactUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update authority contact."""
    service = AuthorityContactService(db)

    update_data = request.model_dump(exclude_unset=True)

    if "contact_type" in update_data:
        try:
            update_data["contact_type"] = ContactType(update_data["contact_type"])
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid contact type: {update_data['contact_type']}",
            )

    try:
        contact = service.update_contact(contact_id, **update_data)
        return AuthorityContactResponse.model_validate(contact)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/authority-contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_authority_contact(contact_id: int, db: DBSession, user: CurrentUser):
    """Delete authority contact (ADVISOR only)."""
    service = AuthorityContactService(db)

    try:
        service.delete_contact(contact_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))