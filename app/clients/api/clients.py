from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.models.client import ClientStatus
from app.clients.schemas.client import (
    ClientConflictInfo,
    ClientListResponse,
    CreateClientRequest,
    CreateClientResponse,
    ClientResponse,
    ClientUpdateRequest,
    ActiveClientSummary,
    DeletedClientSummary,
)
from app.clients.services.create_client_service import CreateClientService
from app.clients.services.client_service import ClientService
from app.core.exceptions import ConflictError
from app.clients.api.client_enrichment import enrich_single, enrich_list

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


# ─── Create ───────────────────────────────────────────────────────────────────

def _raise_client_conflict(service: ClientService, id_number: str, error: ConflictError):
    conflict_info = service.get_conflict_info(id_number)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": error.code,
            "detail": str(error),
            "conflict": ClientConflictInfo(
                id_number=id_number,
                active_clients=[
                    ActiveClientSummary.model_validate(c)
                    for c in conflict_info["active_clients"]
                ],
                deleted_clients=[
                    DeletedClientSummary.model_validate(c)
                    for c in conflict_info["deleted_clients"]
                ],
            ).model_dump(mode="json"),
        },
    )


@router.post(
    "",
    response_model=CreateClientResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def create_client(
    request: CreateClientRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Create a reporting entity and its first business in one request."""
    service = CreateClientService(db)
    try:
        client, business = service.create_client(
            full_name=request.client.full_name,
            id_number=request.client.id_number,
            id_number_type=request.client.id_number_type,
            entity_type=request.client.entity_type,
            phone=request.client.phone,
            email=str(request.client.email) if request.client.email else None,
            address_street=request.client.address_street,
            address_building_number=request.client.address_building_number,
            address_apartment=request.client.address_apartment,
            address_city=request.client.address_city,
            address_zip_code=request.client.address_zip_code,
            vat_reporting_frequency=request.client.vat_reporting_frequency,
            vat_exempt_ceiling=request.client.vat_exempt_ceiling,
            advance_rate=request.client.advance_rate,
            accountant_name=request.client.accountant_name,
            office_client_number=request.client.office_client_number,
            business_name=request.business.business_name,
            business_opened_at=request.business.opened_at,
            business_notes=request.business.notes,
            actor_id=user.id,
        )
    except ConflictError as e:
        if e.code not in {"CLIENT.CONFLICT", "CLIENT.DELETED_EXISTS"}:
            raise
        _raise_client_conflict(service.client_service, request.client.id_number, e)

    return CreateClientResponse(
        client=enrich_single(ClientResponse.model_validate(client), db),
        business=business,
    )


# ─── Read ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=ClientListResponse)
def list_clients(
    db: DBSession,
    search: Optional[str] = Query(None),
    status: Optional[ClientStatus] = Query(None),
    sort_by: str = Query("full_name", pattern="^(full_name|created_at|status)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List clients with optional search, status filter, and sorting."""
    service = ClientService(db)
    items, total = service.list_clients(
        search=search,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    enriched = enrich_list([ClientResponse.model_validate(c) for c in items], db)
    return ClientListResponse(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: DBSession):
    """Get client by ID."""
    service = ClientService(db)
    client = service.get_client_or_raise(client_id)
    return enrich_single(ClientResponse.model_validate(client), db)


@router.get("/conflict/{id_number}", response_model=ClientConflictInfo)
def get_conflict_info(
    id_number: str,
    db: DBSession,
):
    """
    מחזיר מידע על קונפליקטים לת.ז. נתונה.
    משמש את הקליינט לבניית דיאלוג הקונפליקט.
    """
    service = ClientService(db)
    info = service.get_conflict_info(id_number)
    return ClientConflictInfo(
        id_number=id_number,
        active_clients=[ActiveClientSummary.model_validate(c) for c in info["active_clients"]],
        deleted_clients=[DeletedClientSummary.model_validate(c) for c in info["deleted_clients"]],
    )


# ─── Update ───────────────────────────────────────────────────────────────────

@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    request: ClientUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update client identity fields (name, phone, email, address)."""
    service = ClientService(db)
    client = service.update_client(
        client_id,
        actor_id=user.id,
        **request.model_dump(exclude_unset=True),
    )
    return enrich_single(ClientResponse.model_validate(client), db)


# ─── Delete / Restore ─────────────────────────────────────────────────────────

@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_client(client_id: int, db: DBSession, user: CurrentUser):
    """
    Soft-delete a client (ADVISOR only).
    שים לב: אינו מוחק את העסקים של הלקוח — יש למחוק אותם בנפרד.
    """
    service = ClientService(db)
    service.delete_client(client_id, actor_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{client_id}/restore",
    response_model=ClientResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def restore_client(client_id: int, db: DBSession, user: CurrentUser):
    """Restore a soft-deleted client (ADVISOR only)."""
    service = ClientService(db)
    client = service.restore_client(client_id, actor_id=user.id)
    return ClientResponse.model_validate(client)
