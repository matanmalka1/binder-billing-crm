"""Enrichment helpers for ClientResponse — attaches derived fields from related repos."""
from sqlalchemy.orm import Session

from app.clients.schemas.client import ClientResponse
from app.binders.repositories.binder_repository import BinderRepository


def enrich_single(client_resp: ClientResponse, db: Session) -> ClientResponse:
    """Attach active_binder_number to a single ClientResponse."""
    binder_repo = BinderRepository(db)
    active = binder_repo.get_active_by_client(client_resp.id)
    if active:
        client_resp.active_binder_number = active.binder_number
    return client_resp


def enrich_list(items: list[ClientResponse], db: Session) -> list[ClientResponse]:
    """Bulk-enrich a list of ClientResponse objects."""
    if not items:
        return items
    ids = [c.id for c in items]
    binder_repo = BinderRepository(db)
    active_binders = binder_repo.map_active_by_clients(ids)
    for c in items:
        if c.id in active_binders:
            c.active_binder_number = active_binders[c.id].binder_number
    return items
