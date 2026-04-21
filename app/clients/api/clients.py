from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.enums import ClientStatus
from app.clients.schemas.client import (
    ClientConflictInfo,
    CreateClientRequest,
    ClientUpdateRequest,
    ActiveClientSummary,
    DeletedClientSummary,
)
from app.clients.schemas.client_record_response import (
    ClientRecordResponse,
    ClientRecordListResponse,
    ClientRecordListStats,
    CreateClientRecordResponse,
)
from app.clients.schemas.impact import ClientCreationImpactResponse
from app.clients.services.create_client_service import CreateClientService
from app.clients.services.client_service import ClientService
from app.clients.services.impact_preview_service import compute_creation_impact
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_record_read_repository import (
    get_full_record,
    get_full_record_including_deleted,
    get_full_records_bulk,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.clients.api.client_enrichment import enrich_single, enrich_list

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

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


def _full_record_or_404(db, client_record_id: int) -> ClientRecordResponse:
    data = get_full_record(db, client_record_id)
    if not data:
        raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT.NOT_FOUND")
    return ClientRecordResponse(**data)


# ─── Create ───────────────────────────────────────────────────────────────────

@router.post(
    "/preview-impact",
    response_model=ClientCreationImpactResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def preview_creation_impact(
    request: CreateClientRequest,
    _db: DBSession,
):
    """מחזיר תצוגה מקדימה של הישויות שייווצרו אוטומטית עם פתיחת הלקוח. לא כותב לבסיס הנתונים."""
    return compute_creation_impact(
        entity_type=request.client.entity_type,
        vat_reporting_frequency=request.client.vat_reporting_frequency,
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
            business_name=request.business.business_name,
            business_opened_at=request.business.opened_at,
            business_notes=request.business.notes,
            actor_id=user.id,
        )
    except ConflictError as e:
        if e.code not in {"CLIENT.CONFLICT", "CLIENT.DELETED_EXISTS"}:
            raise
        _raise_client_conflict(service.client_service, request.client.id_number, e)

    impact = compute_creation_impact(
        entity_type=request.client.entity_type,
        vat_reporting_frequency=request.client.vat_reporting_frequency,
    )
    full = _full_record_or_404(db, client_record.id)
    return CreateClientRecordResponse(
        client_record_id=client_record.id,
        client=enrich_single(full, db),
        business=business,
        impact=impact,
    )


# ─── Read ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=ClientRecordListResponse)
def list_clients(
    db: DBSession,
    search: Optional[str] = Query(None),
    status: Optional[ClientStatus] = Query(None),
    sort_by: str = Query("official_name", pattern="^(official_name|full_name|created_at|status)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List clients with optional search, status filter, and sorting."""
    repo = ClientRecordRepository(db)
    records = repo.list(
        search=search,
        status=status,
        sort_by="official_name" if sort_by == "full_name" else sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    total = repo.count(search=search, status=status)
    record_ids = [r.id for r in records]
    full_map = get_full_records_bulk(db, record_ids)
    items = [ClientRecordResponse(**full_map[rid]) for rid in record_ids if rid in full_map]
    enriched = enrich_list(items, db)
    counts = repo.count_by_status()
    stats = ClientRecordListStats(
        active=counts.get(ClientStatus.ACTIVE, 0),
        frozen=counts.get(ClientStatus.FROZEN, 0),
        closed=counts.get(ClientStatus.CLOSED, 0),
    )
    return ClientRecordListResponse(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
        stats=stats,
    )


@router.get("/{client_id}", response_model=ClientRecordResponse)
def get_client(client_id: int, db: DBSession):
    """Get client by ID (client_id = ClientRecord.id)."""
    return enrich_single(_full_record_or_404(db, client_id), db)


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
    return enrich_single(_full_record_or_404(db, client_id), db)


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
    data = get_full_record_including_deleted(db, client_id)
    if not data:
        raise NotFoundError(f"רשומת לקוח {client_id} לא נמצאה", "CLIENT.NOT_FOUND")
    return ClientRecordResponse(**data)
