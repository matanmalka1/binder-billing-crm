from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.models.client import ClientStatus
from app.clients.schemas.client import (
    ClientConflictInfo,
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
    ActiveClientSummary,
    DeletedClientSummary,
)
from app.clients.services.client_service import ClientService
from app.core.exceptions import ConflictError
from app.clients.api.client_enrichment import enrich_single, enrich_list

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


# ─── Create ───────────────────────────────────────────────────────────────────

@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(request: ClientCreateRequest, db: DBSession, user: CurrentUser):
    """
    יצירת לקוח חדש (רשומת זהות בלבד).

    מקרי קונפליקט אפשריים:
    - CLIENT.CONFLICT (409): לקוח פעיל עם אותו ת.ז. כבר קיים.
      התגובה כוללת active_clients עם רשימת הלקוחות הפעילים.
    - CLIENT.DELETED_EXISTS (409): לקוח עם אותו ת.ז. קיים אך נמחק.
      התגובה כוללת deleted_clients עם רשימת הלקוחות המחוקים.

    לאחר יצירת לקוח, יש ליצור עסק דרך POST /clients/{client_id}/businesses.
    """
    service = ClientService(db)
    try:
        client = service.create_client(
            full_name=request.full_name,
            id_number=request.id_number,
            id_number_type=request.id_number_type,
            entity_type=request.entity_type,
            phone=request.phone,
            email=str(request.email) if request.email else None,
            address_street=request.address_street,
            address_building_number=request.address_building_number,
            address_apartment=request.address_apartment,
            address_city=request.address_city,
            address_zip_code=request.address_zip_code,
            vat_reporting_frequency=request.vat_reporting_frequency,
            vat_exempt_ceiling=request.vat_exempt_ceiling,
            advance_rate=request.advance_rate,
            accountant_name=request.accountant_name,
            actor_id=user.id,
        )
        return ClientResponse.model_validate(client)
    except ConflictError as e:
        if e.code not in {"CLIENT.CONFLICT", "CLIENT.DELETED_EXISTS"}:
            raise

        conflict_info = service.get_conflict_info(request.id_number)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": e.code,
                "detail": str(e),
                "conflict": ClientConflictInfo(
                    id_number=request.id_number,
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


# ─── Read ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=ClientListResponse)
def list_clients(
    db: DBSession,
    user: CurrentUser,
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
        search=search or None,
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
def get_client(client_id: int, db: DBSession, user: CurrentUser):
    """Get client by ID."""
    service = ClientService(db)
    client = service.get_client_or_raise(client_id)
    return enrich_single(ClientResponse.model_validate(client), db)


@router.get("/conflict/{id_number}", response_model=ClientConflictInfo)
def get_conflict_info(
    id_number: str,
    db: DBSession,
    user: CurrentUser,
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
    return ClientResponse.model_validate(client)


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
