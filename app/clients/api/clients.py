from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.clients.create_policy import derive_id_number_type, preview_vat_reporting_frequency
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.enums import ClientStatus
from app.clients.schemas.client import (
    ClientConflictInfo,
    CreateClientRequest,
    ClientImpactPreviewRequest,
    ClientUpdateRequest,
    ActiveClientSummary,
    DeletedClientSummary,
)
from app.clients.schemas.client_record_response import (
    ClientRecordListResponse,
    ClientRecordResponse,
    CreateClientRecordResponse,
)
from app.clients.schemas.impact import ClientCreationImpactResponse
from app.clients.services.create_client_service import (
    ClientCreationConflictError,
    CreateClientService,
)
from app.clients.services.client_service import ClientService
from app.clients.services.impact_preview_service import compute_creation_impact
from app.businesses.services.client_business_service import ClientBusinessService

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


# ─── Create ───────────────────────────────────────────────────────────────────

@router.post(
    "/preview-impact",
    response_model=ClientCreationImpactResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def preview_creation_impact(
    request: ClientImpactPreviewRequest,
    _db: DBSession,
):
    """מחזיר תצוגה מקדימה של הישויות שייווצרו אוטומטית עם פתיחת הלקוח. לא כותב לבסיס הנתונים."""
    return compute_creation_impact(
        entity_type=request.client.entity_type,
        vat_reporting_frequency=preview_vat_reporting_frequency(
            request.client.entity_type,
            request.client.vat_reporting_frequency,
        ),
        advance_rate=request.client.advance_rate,
    )


@router.post(
    "",
    response_model=CreateClientRecordResponse,
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
        client_record, business = service.create_client(
            full_name=request.client.full_name,
            id_number=request.client.id_number,
            id_number_type=derive_id_number_type(request.client.entity_type),
            entity_type=request.client.entity_type,
            phone=request.client.phone,
            email=str(request.client.email) if request.client.email else None,
            address_street=request.client.address_street,
            address_building_number=request.client.address_building_number,
            address_apartment=request.client.address_apartment,
            address_city=request.client.address_city,
            address_zip_code=request.client.address_zip_code,
            vat_reporting_frequency=request.client.vat_reporting_frequency,
            vat_exempt_ceiling=None,
            advance_rate=request.client.advance_rate,
            accountant_id=request.client.accountant_id,
            business_name=request.business.business_name,
            business_opened_at=request.business.opened_at,
            business_notes=request.business.notes,
            actor_id=user.id,
        )
    except ClientCreationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.detail,
        ) from exc

    impact = compute_creation_impact(
        entity_type=request.client.entity_type,
        vat_reporting_frequency=preview_vat_reporting_frequency(
            request.client.entity_type,
            request.client.vat_reporting_frequency,
        ),
        advance_rate=request.client.advance_rate,
    )
    full = service.client_service.get_full_client(client_record.id)
    business_response = ClientBusinessService(db).to_response(
        business,
        user.role,
        client_id=client_record.id,
    )
    return CreateClientRecordResponse(
        client_record_id=client_record.id,
        client=full,
        business=business_response,
        impact=impact,
    )


# ─── Read ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=ClientRecordListResponse)
def list_clients(
    db: DBSession,
    search: Optional[str] = Query(None),
    status: Optional[ClientStatus] = Query(None),
    accountant_id: Optional[int] = Query(None, ge=1),
    sort_by: str = Query("official_name", pattern="^(official_name|full_name|created_at|status)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List clients with optional search, status filter, and sorting."""
    service = ClientService(db)
    result = service.list_full_clients(
        search=search,
        status=status,
        accountant_id=accountant_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/{client_id}", response_model=ClientRecordResponse)
def get_client(client_id: int, db: DBSession):
    """Get client by ID (client_id = ClientRecord.id)."""
    service = ClientService(db)
    return service.get_full_client(client_id)


@router.get("/conflict/{id_number}", response_model=ClientConflictInfo)
def get_conflict_info(
    id_number: str,
    db: DBSession,
):
    """מחזיר מידע על קונפליקטים לת.ז. נתונה."""
    service = ClientService(db)
    info = service.get_conflict_info(id_number)
    return ClientConflictInfo(
        id_number=id_number,
        active_clients=[ActiveClientSummary.model_validate(c) for c in info["active_clients"]],
        deleted_clients=[DeletedClientSummary.model_validate(c) for c in info["deleted_clients"]],
    )


# ─── Update ───────────────────────────────────────────────────────────────────

@router.patch("/{client_id}", response_model=ClientRecordResponse)
def update_client(
    client_id: int,
    request: ClientUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update client identity fields by ClientRecord.id."""
    service = ClientService(db)
    service.update_client(
        client_id,
        actor_id=user.id,
        actor_role=user.role,
        **request.model_dump(exclude_unset=True),
    )
    return service.get_full_client(client_id)


# ─── Delete / Restore ─────────────────────────────────────────────────────────

@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_client(client_id: int, db: DBSession, user: CurrentUser):
    """Soft-delete a client (ADVISOR only)."""
    service = ClientService(db)
    service.delete_client(client_id, actor_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{client_id}/restore",
    response_model=ClientRecordResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def restore_client(client_id: int, db: DBSession, user: CurrentUser):
    """Restore a soft-deleted client (ADVISOR only)."""
    service = ClientService(db)
    service.restore_client(client_id, actor_id=user.id)
    return service.get_full_client_including_deleted(client_id)
