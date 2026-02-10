from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.schemas.search import SearchResponse, SearchResult
from app.services.search_service import SearchService

router = APIRouter(
    prefix="/search",
    tags=["search"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=SearchResponse)
def search(
    db: DBSession,
    user: CurrentUser,
    query: Optional[str] = None,
    client_name: Optional[str] = None,
    id_number: Optional[str] = None,
    binder_number: Optional[str] = None,
    work_state: Optional[str] = None,
    has_signals: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Unified search for clients and binders."""
    service = SearchService(db)
    results, total = service.search(
        query=query,
        client_name=client_name,
        id_number=id_number,
        binder_number=binder_number,
        work_state=work_state,
        has_signals=has_signals,
        page=page,
        page_size=page_size,
    )

    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        page=page,
        page_size=page_size,
        total=total,
    )