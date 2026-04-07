"""Enrichment helpers for ClientResponse — attaches derived fields from related repos."""
from sqlalchemy.orm import Session

from app.clients.schemas.client import ClientResponse
from app.businesses.repositories.business_repository import BusinessRepository
from app.binders.repositories.binder_repository import BinderRepository


def enrich_single(client_resp: ClientResponse, db: Session) -> ClientResponse:
    """Attach primary_business_type and active_binder_number to a single ClientResponse."""
    biz_repo = BusinessRepository(db)
    binder_repo = BinderRepository(db)
    businesses = biz_repo.list_by_client(client_resp.id, page=1, page_size=1)
    if businesses:
        client_resp.primary_business_type = businesses[0].business_type
    active = binder_repo.get_active_by_client(client_resp.id)
    if active:
        client_resp.active_binder_number = active.binder_number
    return client_resp


def enrich_list(items: list[ClientResponse], db: Session) -> list[ClientResponse]:
    """Bulk-enrich a list of ClientResponse objects."""
    if not items:
        return items
    ids = [c.id for c in items]
    biz_repo = BusinessRepository(db)
    binder_repo = BinderRepository(db)
    businesses = biz_repo.list_by_client_ids(ids)
    first_biz: dict[int, str] = {}
    for b in businesses:
        if b.client_id not in first_biz:
            first_biz[b.client_id] = b.business_type
    active_binders = binder_repo.map_active_by_clients(ids)
    for c in items:
        if c.id in first_biz:
            c.primary_business_type = first_biz[c.id]
        if c.id in active_binders:
            c.active_binder_number = active_binders[c.id].binder_number
    return items
