
from fastapi import APIRouter, Depends, Query

from app.binders.models.binder import BinderStatus
from app.clients.enums import ClientStatus
from app.common.enums import EntityType
from app.search.schemas.search import SearchResponse, SearchResult
from app.search.services.search_service import SearchService
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole

router = APIRouter(
    prefix="/search",
    tags=["search"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=SearchResponse)
def search(
    db: DBSession,
    user: CurrentUser,
    query: str | None = None,
    client_name: str | None = None,
    id_number: str | None = None,
    binder_number: str | None = None,
    client_status: ClientStatus | None = None,
    entity_type: EntityType | None = None,
    binder_status: BinderStatus | None = None,
    filename: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Unified search for clients and binders."""
    service = SearchService(db)
    results, total, documents = service.search(
        query=query,
        client_name=client_name,
        id_number=id_number,
        binder_number=binder_number,
        client_status=client_status,
        entity_type=entity_type,
        binder_status=binder_status,
        filename=filename,
        page=page,
        page_size=page_size,
    )

    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        documents=documents,
        page=page,
        page_size=page_size,
        total=total,
    )
