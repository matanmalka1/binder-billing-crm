from app.binders.schemas.binder import BinderResponse
from app.binders.services.binder_service import BinderService
from app.users.api.deps import DBSession


def fetch_client_and_build_response(binder, db: DBSession) -> BinderResponse:
    """Build BinderResponse via service-layer enrichment only."""
    service = BinderService(db)
    enriched = service.get_binder_with_client_name(binder.id)
    return enriched or service.build_binder_response(binder)
