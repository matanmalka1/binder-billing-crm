from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.authority_contact.schemas.authority_contact import (
    AuthorityContactCreateRequest,
    AuthorityContactListResponse,
    AuthorityContactResponse,
    AuthorityContactUpdateRequest,
)
from app.authority_contact.services.authority_contact_service import AuthorityContactService

router = APIRouter(
    prefix="/businesses",
    tags=["authority-contacts"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.post(
    "/{business_id}/authority-contacts",
    response_model=AuthorityContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_authority_contact(
    business_id: int,
    request: AuthorityContactCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Create new authority contact for client."""
    service = AuthorityContactService(db)

    contact = service.add_contact(
        business_id=business_id,
        contact_type=request.contact_type,
        name=request.name,
        office=request.office,
        phone=request.phone,
        email=request.email,
        notes=request.notes,
    )
    return AuthorityContactResponse.model_validate(contact)


@router.get("/{business_id}/authority-contacts", response_model=AuthorityContactListResponse)
def list_authority_contacts(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    contact_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List authority contacts for client with pagination."""
    service = AuthorityContactService(db)

    contacts, total = service.list_business_contacts(
        business_id,
        contact_type,
        page=page,
        page_size=page_size,
    )

    return AuthorityContactListResponse(
        items=[AuthorityContactResponse.model_validate(c) for c in contacts],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/authority-contacts/{contact_id}",
    response_model=AuthorityContactResponse,
)
def get_authority_contact(
    contact_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """Get a single authority contact by ID."""
    service = AuthorityContactService(db)
    contact = service.get_contact(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"איש קשר {contact_id} לא נמצא",
        )
    return AuthorityContactResponse.model_validate(contact)


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

    contact = service.update_contact(contact_id, **update_data)
    return AuthorityContactResponse.model_validate(contact)


@router.delete(
    "/authority-contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_authority_contact(contact_id: int, db: DBSession, user: CurrentUser):
    """Delete authority contact (ADVISOR only)."""
    service = AuthorityContactService(db)

    service.delete_contact(contact_id, actor_id=user.id)
